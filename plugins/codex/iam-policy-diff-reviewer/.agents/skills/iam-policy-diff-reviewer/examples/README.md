`python scripts/iam_diff.py examples/old-policy.json examples/new-policy.json` exits 1 with three findings:
1. statement 0: `s3:PutObject` added to an existing Allow (medium)
2. statement 1: new `iam:PassRole` on `*` (high)
3. old statement 1: the Deny on `s3:DeleteObject` was removed (high)
