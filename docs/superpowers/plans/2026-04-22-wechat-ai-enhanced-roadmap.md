# WeChat AI Enhanced Roadmap

> This roadmap decomposes `PROJECT_PLAN.md` into independent implementation plans that can be executed and verified incrementally.

## Workstreams

1. `2026-04-22-wechat-ai-foundation-refactor.md`
   - Establish the target package layout without breaking the current 4.1+ auto-reply entrypoints.
   - Add shared data directories, base models, and migration-friendly module boundaries.

2. `2026-04-22-wechat-ai-profiles-and-config.md`
   - Add user profile, agent profile, and centralized runtime configuration.
   - Preserve current MiniMax + prompt behavior while making persona inputs explicit and testable.

3. `2026-04-22-wechat-ai-rag-foundation.md`
   - Add local knowledge ingestion, chunking, embeddings abstraction, and retrieval.
   - Keep the first version file-based and replaceable later.

4. `2026-04-22-wechat-ai-prompt-pipeline.md`
   - Build the orchestration layer that merges message context, persona data, and retrieved knowledge.
   - Rework `reply_engine` into a pipeline-friendly composition root.

5. `2026-04-22-wechat-ai-observability-and-memory.md`
   - Add structured logs, prompt previews, run traces, and lightweight memory summaries.
   - Make debugging and future long-term memory upgrades practical.

## Delivery Order

1. Foundation refactor
2. Profiles and config
3. RAG foundation
4. Prompt pipeline
5. Observability and memory

## Why This Order

- The current codebase already has a working `wechat_ai` runtime, so the safest path is to keep entrypoints stable and add extension seams first.
- Profiles and config are prerequisites for meaningful prompt orchestration.
- RAG should land before the final prompt builder so the pipeline can be designed around actual retrieval outputs instead of placeholders.
- Observability and memory should follow the main pipeline so logs reflect the real end-to-end execution path.

## Integration Guardrails

- Do not break these entrypoints while implementing the plan set:
  - `scripts/run_minimax_friend_auto_reply.py`
  - `scripts/run_minimax_group_at_reply.py`
  - `scripts/run_minimax_global_auto_reply.py`
- Preserve current environment-variable support for MiniMax during the first rollout.
- Keep `pyweixin` as the message transport and UI automation layer; all new AI enhancements should remain additive inside `wechat_ai`.
- Favor file-backed JSON/Markdown stores for MVP instead of introducing a database early.

## Suggested Validation Gates

- After Workstream 1: current unit tests still pass and existing CLI entrypoints still import successfully.
- After Workstream 2: persona-aware reply generation can be exercised with local fixture data.
- After Workstream 3: knowledge ingestion + retrieval can be tested independently from WeChat runtime.
- After Workstream 4: end-to-end prompt assembly includes context, profiles, and retrieval results.
- After Workstream 5: failures and fallback replies become diagnosable from structured logs.
