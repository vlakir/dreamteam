"""
Jinja extensions for the dreamteam Copier template.

These ship inside the installed `dreamteam` package (not as template
data) and are referenced from the template's `copier.yml` by their
installed dotted path, e.g.::

    _jinja_extensions:
      - dreamteam._jinja_ext.frontmatter.FrontmatterExtension

Copier resolves `_jinja_extensions` via a normal Python import against
the running environment — which always has `dreamteam` installed when
`dreamteam init` / `dreamteam update` runs — so the extension loads
identically whether copier renders from the wheel-shipped template
(init) or from the `.bundle` clone (update). This avoids putting the
extension on `sys.path` (copier 9.x does not add the template root)
and keeps it out of derived projects.
"""
