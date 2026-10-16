"""Child-process crash barrier for T171, intentionally no finally/rollback.

The parent observes a marker and SIGKILL exit, proving the selected transaction
window was reached in a separate process. No source or provider secrets enter
the marker; operation identifiers remain opaque.
"""

from pathlib import Path
import os
import signal
import sys

from dreamteam import migration_store
from dreamteam.cli import app


root, stop_event, marker = sys.argv[1:]


def crash(event, operation_id):
    if event == stop_event:
        path = Path(marker)
        with path.open('w') as stream:
            stream.write(event)
            stream.flush()
            os.fsync(stream.fileno())
        os.kill(os.getpid(), signal.SIGKILL)


replace = Path.replace


def crash_after_answers(path, destination, *args, **kwargs):
    result = replace(path, destination, *args, **kwargs)
    # Observe the real atomic publication of public completion metadata, then
    # kill before the caller can acknowledge/finalize its recovery record.
    if Path(destination) == Path(root) / '.copier-answers.yml':
        crash('answers_published', None)
    return result


Path.replace = crash_after_answers
migration_store.checkpoint = crash
sys.argv = ['dreamteam', 'apply', root, '--defaults', '--on-conflict', 'keep']
app()
