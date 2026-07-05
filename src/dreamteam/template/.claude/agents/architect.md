{%- set _raw %}{% include 'partials/architect.body.' ~ language ~ '.md' %}{% endset -%}
{%- set _body = _raw | strip_frontmatter -%}
---
name: architect
description: {{ _body | md_comment_value('description') | yaml_str }}
tools: Read, Glob, Grep
model: {{ architect_model }}
---
{{ _body | strip_leading_comment }}
