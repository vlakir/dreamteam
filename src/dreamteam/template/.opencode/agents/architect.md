{%- set _raw %}{% include 'partials/architect.body.' ~ language ~ '.md' %}{% endset -%}
{%- set _body = _raw | strip_frontmatter -%}
---
description: {{ _body | md_comment_value('description') | yaml_str }}
mode: subagent
{% if architect_model and architect_model != 'inherit' -%}
model: {{ architect_model | yaml_str }}
{% endif -%}
permission:
  "*": deny
  read: allow
  glob: allow
  grep: allow
  list: allow
  team_message: allow
  team_broadcast: allow
  team_results: allow
  team_tasks_list: allow
  team_tasks_complete: allow
---
{{ _body | strip_leading_comment }}

Also perform requirements analysis: identify missing requirements, acceptance criteria, constraints and API contracts. Return open questions to the lead; do not decide product scope on behalf of the user.
