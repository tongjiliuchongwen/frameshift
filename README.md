# Frameshift

Frameshift is a research-reframing project with three maintained editions.

This `master` branch is intentionally a lightweight index. The implementation
branches are kept separate because each branch targets a different agent
runtime and carries different gate mechanics.

## Maintained Branches

| Branch | Runtime | Status | Contents |
| --- | --- | --- | --- |
| [`claude`](https://github.com/tongjiliuchongwen/frameshift/tree/claude) | Claude Code | v0.5.1 | Original Research Reframer skill pack with Claude-oriented gate flow. |
| [`codex`](https://github.com/tongjiliuchongwen/frameshift/tree/codex) | Codex | v0.7.0-codex | Codex-first Research Reframer pack with Stage 0 diagnosis and Codex App Server gate sidecar. |
| [`antigravity`](https://github.com/tongjiliuchongwen/frameshift/tree/antigravity) | Antigravity | v0.7.0-codex | Antigravity-oriented Codex pack with polling support and Antigravity example workflow. |

## Legacy Branch

The previous `master` content has been archived without modification at
[`legacy/frameshift-m3`](https://github.com/tongjiliuchongwen/frameshift/tree/legacy/frameshift-m3).

That branch contains the older Frameshift M3 dashboard and engine experiment.
It is preserved for reference, but it is not the recommended entry point for
new users.

## Choosing a Branch

Use `claude` if you are running the workflow inside Claude Code.

Use `codex` if you are running the workflow inside Codex and want browser-button
gates through the local Codex App Server sidecar.

Use `antigravity` if you are running the Antigravity workflow and need the
polling-oriented gate support.

Example:

```bash
git clone --branch codex https://github.com/tongjiliuchongwen/frameshift.git
```

## Repository Hygiene

Generated bundles, test runs, caches, logs, and local machine paths should not
be committed. See [`SECURITY.md`](SECURITY.md) for the release checklist used
before publishing the maintained branches.
