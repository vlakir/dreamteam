"""Recovery must preserve ownership, worktrees and nonduplicate delivery."""
import json
import re
import sqlite3
from contextlib import closing
import subprocess
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from dreamteam.cli import app
import pytest
from dreamteam.recovery import interrupted, resume_member, _request

@pytest.fixture
def recovery(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'opencode.json').write_text(json.dumps({'plugin': ['@hueyexe/opencode-ensemble@0.18.0']}))
    worktree = tmp_path / 'worktree'
    worktree.mkdir()
    (worktree / 'proof.txt').write_text('stage-one\n')
    db = tmp_path / 'ensemble.db'
    with closing(sqlite3.connect(db)) as c, c:
        c.executescript("""
        CREATE TABLE team(id TEXT, project_id TEXT, status TEXT, lead_session_id TEXT, name TEXT);
        CREATE TABLE team_member(team_id TEXT, name TEXT, session_id TEXT, status TEXT,
          execution_status TEXT, worktree_dir TEXT, worktree_branch TEXT, model TEXT, agent TEXT,
          reported_to_lead INTEGER, time_updated INTEGER);
        CREATE TABLE team_task(id TEXT, team_id TEXT, status TEXT, depends_on TEXT,
          assignee TEXT, time_updated INTEGER);
        """)
        c.execute('INSERT INTO team VALUES(?,?,?,?,?)', ('team', str(project), 'active', 'lead', 'test'))
        c.execute('INSERT INTO team_member VALUES(?,?,?,?,?,?,?,?,?,?,?)',
          ('team', 'worker', 'child', 'error', 'idle', str(worktree), 'same', 'provider/model', 'backend', 0, 0))
        c.execute('INSERT INTO team_task VALUES(?,?,?,?,?,?)', ('task', 'team', 'pending', None, None, 0))
    kwargs = dict(server='http://127.0.0.1:4096', member='worker', lead_session='lead',
                  task='task', backup_dir=tmp_path/'backups')
    return project, worktree, db, kwargs

def request_for(project):
    def request(server, path, body=None):
        if path == '/global/health': return {'version':'1.19.0'}
        if path == '/session/child': return {'parentID':'lead'}
        if path == '/session/lead': return {'directory':str(project)}
        if path == '/session/status': return {}
        return {}
    return request

def test_recovery_preserves_existing_work_and_rejects_second_delivery(recovery):
    project, worktree, db, kwargs = recovery
    with patch('dreamteam.recovery._request',side_effect=request_for(project)) as api, patch('dreamteam.recovery._git_value',return_value='same'):
        assert resume_member(project,db,**kwargs) == 'child'
        delivery = api.call_args
        assert '/session/child/prompt_async?' in delivery.args[1]
        assert delivery.args[2]['model'] == {'providerID':'provider','modelID':'model'}
        assert str(worktree) in delivery.args[2]['parts'][0]['text']
        with pytest.raises(RuntimeError,match='Expected one interrupted'):
            resume_member(project,db,**kwargs)
        assert sum('/prompt_async?' in c.args[1] for c in api.call_args_list) == 1
    assert (worktree/'proof.txt').read_text() == 'stage-one\n'
    with closing(sqlite3.connect(db)) as c, c:
        assert c.execute('SELECT status,assignee FROM team_task').fetchone() == ('in_progress','worker')
    assert len(list(kwargs['backup_dir'].glob('*.sqlite'))) == 1

@pytest.mark.parametrize('case', ['wrong_lead','wrong_project','missing_worktree','foreign_repo','running','claimed','dependency'])
def test_recovery_stops_before_mutation(recovery,case):
    project, worktree, db, kwargs = recovery
    request = request_for(project)
    git = lambda path,*args: 'same'
    if case=='wrong_lead': kwargs['lead_session']='someone-else'
    if case=='wrong_project':
        with closing(sqlite3.connect(db)) as c, c:c.execute("UPDATE team SET project_id='elsewhere'")
    if case=='missing_worktree': (worktree/'proof.txt').unlink();worktree.rmdir()
    if case=='foreign_repo':git=lambda path,*args:str(path)
    if case=='running':
        original=request
        request=lambda server,path,body=None: {'child':{'type':'busy'}} if path=='/session/status' else original(server,path,body)
    if case=='claimed':
        with closing(sqlite3.connect(db)) as c, c:c.execute("UPDATE team_task SET status='in_progress', assignee='other'")
    if case=='dependency':
        with closing(sqlite3.connect(db)) as c, c:c.execute('UPDATE team_task SET depends_on=?',(json.dumps(['missing']),))
    with patch('dreamteam.recovery._request',side_effect=request) as api,patch('dreamteam.recovery._git_value',side_effect=git):
        with pytest.raises(RuntimeError):resume_member(project,db,**kwargs)
        assert not any('/prompt_async?' in c.args[1] for c in api.call_args_list)
    with closing(sqlite3.connect(db)) as c, c:
        assert c.execute('SELECT status FROM team_member').fetchone()[0]=='error'

def test_uncertain_delivery_is_not_automatically_retried(recovery):
    project,worktree,db,kwargs=recovery
    original=request_for(project)
    def request(server,path,body=None):
        if '/prompt_async?' in path:raise RuntimeError('connection lost')
        return original(server,path,body)
    with patch('dreamteam.recovery._request',side_effect=request),patch('dreamteam.recovery._git_value',return_value='same'):
        with pytest.raises(RuntimeError,match='Delivery uncertain'):resume_member(project,db,**kwargs)
        with pytest.raises(RuntimeError,match='Expected one interrupted'):resume_member(project,db,**kwargs)
    with closing(sqlite3.connect(db)) as c, c:assert c.execute('SELECT status FROM team_member').fetchone()[0]=='ready'

def test_listing_is_project_scoped_and_read_only(recovery):
    project,worktree,db,kwargs=recovery
    before=db.read_bytes()
    assert len(interrupted(project,db))==1
    assert interrupted(project/'different',db)==[]
    assert db.read_bytes()==before

@pytest.mark.parametrize('url',['https://example.org','http://192.168.1.1','http://127.0.0.1/prefix'])
def test_recovery_refuses_nonlocal_server(url):
    with pytest.raises(RuntimeError,match='loopback'):_request(url,'/global/health')


def test_team_archived_during_recovery_cannot_be_resurrected(recovery):
    project,worktree,db,kwargs=recovery
    def git(path,*args):
        with closing(sqlite3.connect(db)) as c, c:c.execute("UPDATE team SET status='archived'")
        return 'same'
    with patch('dreamteam.recovery._request',side_effect=request_for(project)),patch('dreamteam.recovery._git_value',side_effect=git):
        with pytest.raises(RuntimeError,match='changed concurrently'):resume_member(project,db,**kwargs)
    with closing(sqlite3.connect(db)) as c, c:
        assert c.execute('SELECT status FROM team_member').fetchone()[0]=='error'
        assert c.execute('SELECT status FROM team_task').fetchone()[0]=='pending'

@pytest.mark.parametrize('case',['wrong_version','foreign_parent','foreign_directory'])
def test_server_identity_must_match_database(recovery,case):
    project,worktree,db,kwargs=recovery
    original=request_for(project)
    def request(server,path,body=None):
        if case=='wrong_version' and path=='/global/health':return {'version':'2.0.0'}
        if case=='foreign_parent' and path=='/session/child':return {'parentID':'other'}
        if case=='foreign_directory' and path=='/session/lead':return {'directory':'elsewhere'}
        return original(server,path,body)
    with patch('dreamteam.recovery._request',side_effect=request):
        with pytest.raises(RuntimeError):resume_member(project,db,**kwargs)
    with closing(sqlite3.connect(db)) as c, c:assert c.execute('SELECT status FROM team_member').fetchone()[0]=='error'

@pytest.mark.parametrize('status,body,exception',[(200,b'{"ok":true}',None),(204,b'',None),(500,b'failure',RuntimeError),(200,b'not-json',RuntimeError),(200,b'[]',TypeError)])
def test_recovery_http_protocol(status,body,exception):
    conn=MagicMock();response=conn.getresponse.return_value.__enter__.return_value
    response.status=status;response.read.return_value=body
    with patch('dreamteam.recovery.HTTPConnection',return_value=conn):
        if exception:
            with pytest.raises(exception):_request('http://127.0.0.1:4096','/health')
        else:
            result=_request('http://127.0.0.1:4096','/health')
            assert result==({'ok':True} if body else {})
    conn.close.assert_called_once()

def test_recovery_connection_failure_is_actionable():
    with patch('dreamteam.recovery.HTTPConnection',side_effect=OSError('offline')):
        with pytest.raises(RuntimeError,match='connection failed'):_request('http://127.0.0.1:4096','/health')


def test_cli_recovery_requires_exact_member_and_task(recovery):
    project,worktree,db,kwargs=recovery
    result=CliRunner().invoke(app,['recover',str(project),'--member','worker'])
    assert result.exit_code!=0
    output = re.sub(r'\x1b\[[0-9;]*m', '', result.output)
    assert '--lead-session and --task' in ' '.join(output.split())


def test_invalid_stored_model_stops_before_claiming_task(recovery):
    project,worktree,db,kwargs=recovery
    with closing(sqlite3.connect(db)) as c, c:c.execute("UPDATE team_member SET model='legacy-alias'")
    with patch('dreamteam.recovery._request',side_effect=request_for(project)),patch('dreamteam.recovery._git_value',return_value='same'):
        with pytest.raises(RuntimeError,match='provider/model-id'):resume_member(project,db,**kwargs)
    with closing(sqlite3.connect(db)) as c, c:
        assert c.execute('SELECT status FROM team_member').fetchone()[0]=='error'
        assert c.execute('SELECT status FROM team_task').fetchone()[0]=='pending'


@pytest.mark.parametrize('stored,actual,head,preserved',[
    ('same','different','a','a'),
    ('ensemble/preserved/team/worker','unrelated','a','a'),
    ('ensemble/preserved/team/worker','opencode/worktree','new','old'),
])
def test_recovery_cannot_take_over_repurposed_branch(recovery,stored,actual,head,preserved):
    project,worktree,db,kwargs=recovery
    with closing(sqlite3.connect(db)) as c, c:c.execute('UPDATE team_member SET worktree_branch=?',(stored,))
    def git(path,*args):
        if args[0]=='symbolic-ref':return actual
        if '--git-common-dir' in args:return 'common'
        return head if args[-1]=='HEAD' else preserved
    with patch('dreamteam.recovery._request',side_effect=request_for(project)) as api,patch('dreamteam.recovery._git_value',side_effect=git):
        with pytest.raises(RuntimeError):resume_member(project,db,**kwargs)
        assert not any('/prompt_async?' in call.args[1] for call in api.call_args_list)
    with closing(sqlite3.connect(db)) as c, c:
        assert c.execute('SELECT status FROM team_member').fetchone()[0]=='error'
        assert c.execute('SELECT status FROM team_task').fetchone()[0]=='pending'


def test_recovery_preserved_ref_with_real_git_worktree(recovery):
    project,worktree,db,kwargs=recovery
    def git(*args,cwd=project):
        return subprocess.run(['git','-C',str(cwd),*args],check=True,capture_output=True,text=True).stdout.strip()
    git('init','-q')
    git('config','user.name','Recovery Test')
    git('config','user.email','test@example.invalid')
    git('config','commit.gpgsign','false')
    git('add','opencode.json');git('commit','-qm','Initial fixture')
    proof=(worktree/'proof.txt').read_bytes();(worktree/'proof.txt').unlink();worktree.rmdir()
    git('worktree','add','-q','-b','opencode/worktree',str(worktree))
    (worktree/'proof.txt').write_bytes(proof)
    preserved='ensemble/preserved/team/worker';git('branch',preserved)
    with closing(sqlite3.connect(db)) as c, c:c.execute('UPDATE team_member SET worktree_branch=?',(preserved,))
    with patch('dreamteam.recovery._request',side_effect=request_for(project)) as api:
        assert resume_member(project,db,**kwargs)=='child'
        assert '/prompt_async?' in api.call_args.args[1]
    assert (worktree/'proof.txt').read_bytes()==proof
    with closing(sqlite3.connect(db)) as c, c:assert c.execute('SELECT worktree_branch FROM team_member').fetchone()[0]=='opencode/worktree'
