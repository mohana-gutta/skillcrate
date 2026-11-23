# Rules

| ID | Severity | Condition |
|---|---|---|
| CK001 | warning | `key` has no hashFiles() and no github.* expression. The key is constant, so the cache is written once and never refreshed. |
| CK002 | error | A literal hashFiles() glob matches no regular file under the repo root. The hash is the same on every run. Globs that escape the repo are reported as possible, not evaluated. |
| CK003 | possible | The workflow has a `matrix:` and the key contains neither `runner.os` nor `matrix.` values. Different matrix legs may overwrite or restore each other's caches. |
| CK004 | possible | hashFiles() over `**`, `*`, `**/*` or similar. Any file change alters the key. |
| CK006 | warning | A `restore-keys` entry's literal prefix and the key's literal prefix do not overlap, so the fallback never matches. |

Keys with `github.sha`, `run_id` or `run_number` and no restore-keys never hit. That is a known gap (planned CK008), not implemented.
