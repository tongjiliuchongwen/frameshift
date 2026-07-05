# Security And Release Hygiene

Before publishing a branch, check for:

- Local absolute paths, including Windows drive-root paths and user-home paths.
- Personal machine names, local workspace paths, thread ids, and generated logs.
- Secret-looking values such as GitHub tokens, OpenAI API keys, AWS keys, bearer tokens, and private keys.
- Generated directories such as `dist/`, `test-runs/`, `__pycache__/`, `node_modules/`, and `tmp/`.
- Broken or partial examples that do not validate under the branch's current schema.

Use `git grep` or a secret scanner before publishing. Keep scanner patterns in
private tooling instead of committing them here, so this file does not create
self-referential false positives.

If a published branch already contains a sensitive path or secret in history,
rewrite that branch after backing up any useful non-sensitive content.
