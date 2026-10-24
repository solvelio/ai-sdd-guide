# Repo Agent Routing Rules

These rules apply to development work in this `ai-sdd-guide` repository only.
They are not part of the consumer-facing SDD contract unless explicitly copied
into a downstream project.

## Model and Agent Assignment

| Work type | Owner | Model / backend | Requirement |
|---|---|---|---|
| Issue triage and issue creation | Codex orchestrator | `gpt-5.5`, reasoning `medium` | Define scope, acceptance criteria, dependencies, and follow-up links. |
| PR review and merge decision | Codex reviewer | `gpt-5.5`, reasoning `medium` | Review from a bug/risk stance; verify CI before merge. |
| Issue implementation through PR creation | vLLM implementer | Qwen via vLLM | Make the code/docs changes from a self-contained brief. |
| Implementation review before PR ready | independent reviewer subagent | `gpt-5.4-mini` | Read-only review of the implementation diff vs the frozen spec. |
| Critical or Important review fixes | vLLM implementer | Qwen via vLLM | Apply concrete review findings without redesigning scope. |

## Operating Rules

- Codex is the orchestrator and reviewer for this repository. When vLLM is
  available, Codex should not be the primary implementation agent.
- vLLM receives a self-contained implementation brief: issue URL, spec path,
  task list, allowed write scope, required tests, and report path.
- vLLM must not edit frozen specs, `freeze.json`, or unrelated files unless
  the brief explicitly grants that scope.
- The `gpt-5.4-mini` reviewer is read-only. It may inspect diffs and run tests,
  but must not fix findings.
- `gpt-5.5` with reasoning `medium` performs issue creation, final PR review,
  and merge/no-merge decisions.
- If vLLM is unavailable or cannot edit the workspace, Codex must state that
  limitation and ask whether to proceed with Codex implementation.

## vLLM Backend Contract

Do not commit endpoint secrets or API keys. Configure the vLLM implementer with
environment variables or local operator config:

- `VLLM_BASE_URL`: OpenAI-compatible vLLM endpoint.
- `VLLM_MODEL`: Qwen model name exposed by vLLM.
- `VLLM_API_KEY`: optional, only when the endpoint requires authentication.

Codex should pass implementation briefs to the vLLM backend through the local
wrapper or OpenAI-compatible `/chat/completions` API, then verify the resulting
workspace diff before requesting `gpt-5.4-mini` review.

## Review Flow

1. `gpt-5.5 medium` creates or refines the issue and confirms scope.
2. Codex prepares a brief and delegates implementation to vLLM/Qwen.
3. vLLM implements, runs focused tests, and reports changed files and results.
4. Codex inspects the diff and asks `gpt-5.4-mini` for an independent review.
5. vLLM fixes Critical or Important review findings.
6. `gpt-5.5 medium` performs final PR review, checks CI, and decides merge.
