# First card walkthrough

The starter requires Git and Python 3.9 or later. It uses no Python packages or API keys. Run commands from the repository root unless another directory is specified.

## Inspect the prepared pilot

```sh
git status --short
git worktree list
python3 scripts/fleet.py list
python3 -m unittest discover -s tests -v
```

The initial pilot is `FLEET-001`. Its branch is `fleet/FLEET-001`. On the original setup computer, its worktree already exists in the sibling `codex-fleet-worktrees/FLEET-001` folder. A fresh clone does not inherit local worktrees. Use `git worktree list` to check before creating one; `start` refuses to replace an existing branch or worktree. The CLI names the sibling worktree directory after your checkout, so cloning as `Fleet` produces `Fleet-worktrees/`. Worktree creation does not launch an agent.

## Give an author a new task

From a clean main checkout, create a local intake branch and choose a previously unused ID. This keeps the card commit off protected `main`:

```sh
git switch main
git pull --ff-only origin main
git switch -c intake/FLEET-003
python3 scripts/fleet.py new FLEET-003 'Document project-specific verification commands' --accept 'Document runnable verification commands and their prerequisites'
git add cards/FLEET-003.json
git commit -m 'Add FLEET-003 task'
python3 scripts/fleet.py start FLEET-003
```

The card commit stays on the local intake branch and is included in the implementation branch created by `start`; submit that implementation branch as one PR containing the card and its change. The checkout must be clean before `start`. Open the printed worktree path in Codex and provide its card with the author prompt from `docs/prompts.md`. Worktrees share Git history but have separate files and branches. Do not run two authors in the same worktree.

## Commit and review

After the author completes the work and runs checks, it commits on `fleet/FLEET-003`. In that worktree, inspect `git rev-parse HEAD` and have an independent reviewer review that exact revision against `main`. Record only an actual review, using real session identities:

```sh
python3 scripts/fleet.py review FLEET-003 --author author-session-1 --reviewer reviewer-session-2 --kind agent --verdict pass
python3 scripts/fleet.py ready FLEET-003 --author author-session-1 --base main
```

A documentation-only change generally requires one independent reviewer. Changes to protected paths require a second distinct reviewer, including a human. Record a human review only after a human has performed it:

```sh
python3 scripts/fleet.py review FLEET-003 --author author-session-1 --reviewer human-owner --kind human --verdict pass
python3 scripts/fleet.py ready FLEET-003 --author author-session-1 --base main
```

A fail verdict blocks readiness. The same reviewer can record a later pass after resolving findings. New commits invalidate old records. Update the branch when main has advanced, then repeat validation and review. Readiness also refuses dirty trees and branches with no new commit against main.

## Landing and hosting

The readiness result is advisory; it never merges, deploys, or authenticates reviewers. The pilot's human owner inspects the current revision and approves landing separately. The hosted Fleet repository now requires a pull request, the passing `test` check against an up-to-date branch, resolved review conversations, and an independent approval of the latest push. Stale approvals are dismissed, and administrators cannot bypass the rule. These settings apply to the hosted repository, not automatically to forks or fresh repositories; see `docs/policy.md`. The PR author cannot supply the required GitHub approval themselves. A reviewer with write access must approve before merge; local agent review records do not satisfy that requirement.

The initial test suite verifies ID validation, worktree creation, duplicate-card rejection, stale/self-review rejection, distinct protected-path reviewers, human review requirements, and unresolved failures. It does not establish the quality of a future product's tests.
