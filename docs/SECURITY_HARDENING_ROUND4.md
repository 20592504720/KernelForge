# Round 4 — recovery and concurrency

Baseline 53c98e599ebdf6091c82aa1beab36eaab336072c. No main/PR merge, source lock modifications, or OEM build authorization.

* Directory locks serialize acquisition, stale reclamation and release via persistent OS advisory guards. Owner tokens prevent deleting a replacement lock. Only a demonstrably dead same-host owner may be recovered. Unknown/foreign owner fails closed. Windows uses a non-destructive process handle query. Old workspace locks require manual review; guards must not be removed while in use. Local filesystems only; no claim against a concurrently malicious privileged process.
* Output ownership serialized across distinct workspaces. ccache lease remains active through compiler/config/artefact checks and invalidation. Unknown toolchain use markers block mutation; no auto-expiry. Cache prune validates the key before constructing paths and rejects links/reparse points. 
* Raw generic subprocess diagnostic spool bounded to 128 MiB, checks 64 MiB filesystem reserve, drops truncated line, drains excessive output, preserves direct-child timeout. No physical-host quota or general descendant sandbox. Other evidence producers retain their own policies.
* Stage 7.4 report creation is exclusive. Stage 1–6 one-shot workflow additionally exercises default and custom timestamp Stage 7.4 policy without compiling or syncing OEM sources.
* New offline tests exercise contention, replaced/malformed ownership, cross-workspace output, abandoned leases, invalid keys, noisy subprocess output and failure/timeout/disk checks.
* CodeQL analysis previously succeeded; alert listing not accessible via connector. Bandit B314 residual XML parser warning and subprocess inventory remain. No claim that all findings or race conditions have been eliminated.
* Full software and real pinned ACK6.1 regression must be separately verified on this snapshot; OEM 35-project new sync and local WSL revalidation require the original environment. Keep build_eligible=false for Stage 7.5.

Initial Windows regression at cc6b886e2eac44c955e6a59070d4c4478796f3e4 exposed a staging-to-install path relocation regression after lexical cache-path validation (returned compiler path was stale), plus a CRLF-dependent fixture. Resolve only after checking link ancestry; compute final executable paths from published install root and verify metadata/env; use binary stdout for the byte-exact fixture. Preserve initial failed runs 45302016405 / 45302022345; fresh four-platform tests required.
