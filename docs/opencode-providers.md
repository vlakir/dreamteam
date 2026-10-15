# Providers, models and role assignments

Dreamteam requires OpenCode, not an account with a specific provider. Keep
credentials and provider configuration in personal OpenCode settings. Project
agents inherit models unless explicitly overridden. The same model name at two
providers does not guarantee identical tools, limits, caching or protocol support.

## Preserve the native protocol

Use separate provider entries for endpoints with different protocols, even when
one vendor serves all of them. Anthropic Messages should use `@ai-sdk/anthropic`;
OpenAI Responses should use the native OpenAI provider/SDK and an endpoint that
actually supports Responses. Use an OpenAI-compatible chat adapter when that is
the protocol the endpoint implements. Do not route every model through one chat
adapter and assume vendor features survive.

For a custom Anthropic endpoint, the following is illustrative, not a vendor
recommendation. Replace the model ID, URL, limits and capabilities with actual
provider/model data:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "my-anthropic-route": {
      "npm": "@ai-sdk/anthropic",
      "options": {
        "baseURL": "https://api.example.net/v1",
        "apiKey": "{env:MY_ANTHROPIC_API_KEY}"
      },
      "models": {
        "model-from-catalog": {
          "attachment": true,
          "toolcall": true,
          "modalities": {"input": ["text", "image"], "output": ["text"]},
          "limit": {"context": 128000, "output": 8192}
        }
      }
    }
  }
}
```

Declaring attachment support alone does not declare image input. Missing image
modalities can prevent an image from reaching the model. Declare `reasoning`
only for a supported model, and verify the resulting request/response behavior.
Unknown context/output limits also need attention before relying on compaction.
A provider catalog is useful evidence; a live feature probe is still required.

## Assign models by role

Choose the lead model through OpenCode's model selector, the personal default
`model`, or an agent model override. For Ensemble workers, personal
`~/.config/opencode/ensemble.json` supports:

```json
{
  "mergeOnCleanup": false,
  "promptForModels": false,
  "modelsByAgent": {
    "architect": "provider-a/reasoning-model",
    "backend": "provider-a/coding-model",
    "tester": "provider-a/economical-model",
    "reviewer": "provider-b/review-model"
  }
}
```

Those IDs are placeholders. An explicit model in `team_spawn` overrides the
role mapping. In Ensemble 0.18.0, the order is explicit spawn model, role map,
rotation/random pool, default model, then inheritance. The lead's own model is
not selected by the worker map. Read-only architect/reviewer workers should be
spawned with `worktree:false`, so Ensemble does not add writer permissions.

## Verify capabilities and switching

For each route you plan to use, verify text, streaming, tool calls, actual image
recognition, reasoning where applicable, cancellation and error reporting.
For caching, repeat a sufficiently long stable prefix and inspect cache read/
write usage. Native SDK support is necessary but does not prove the endpoint
accepted cache controls. Cache reuse is provider/model specific; changing models
or providers may rebuild the cache. A zero cost displayed for a custom model
can mean missing pricing metadata, not a free request.

Keep an alternative route configured before you need it. Switch the selected
model/role mapping without changing project methodology, tasks or memory. Check
history compatibility on a bounded session before switching an active team.
Configuration reload can reinitialize Ensemble: schedule configuration changes
when workers are stopped rather than experimenting with parallel standalone
processes against an active project.

OpenCode supports ChatGPT authentication without requiring the Codex executable.
Use its native account login flow. Anthropic subscription integrations are outside
dreamteam's supported setup; Claude API routes remain supported. Personal live
acceptance results are recorded separately from credential-free package tests.
