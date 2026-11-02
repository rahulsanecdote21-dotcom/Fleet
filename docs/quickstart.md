# First card walkthrough

The starter requires Git and Python 3.9 or later. It uses no Python packages or API keys. Run commands from the repository root unless another directory is specified.

## Inspect the prepared pilot

```sh
git status --short
git worktree list
python3 scripts/fleet.py list
python3 -m unittest discover -s tests -v
```

The initial pilot is `FLEET-001`. Its branch is `fleet/FLEET-001`; its worktree is the sibling `codex-fleet-worktrees/FLEET-001` folder. It was already created during setup, so running `start FLEET-001` again should fail rather than replace it. Worktree creation does not launch an agent.

## Give an author a new task

From the main checkout, choose a previously unused ID:

```sh
python3 scripts/fleet.py new FLEET-002 'Document project-specific verification commands' --accept 'Document runnable verification commands and their prerequisites'
git add cards/FLEET-002.json
git commit -m 'Add FLEET-002 task'
python3 scripts/fleet.py start FLEET-002
```

The checkout must be clean before `start`. Open the printed worktree path in Codex and provide its card with the author prompt from `docs/prompts.md`. Worktrees share Git history but have separate files and branches. Do not run two authors in the same worktree.

## Commit and review

After the author completes the work and runs checks, it commits on `fleet/FLEET-002`. In that worktree, inspect `git rev-parse HEAD` and have an independent reviewer review that exact revision against `main`. Record only an actual review, using real session identities:

```sh
python3 scripts/fleet.py review FLEET-002 --author author-session-1 --reviewer reviewer-session-2 --kind agent --verdict pass
python3 scripts/fleet.py ready FLEET-002 --author author-session-1 --base main
```

A documentation-only change generally requires one independent reviewer. Changes to protected paths require a second distinct reviewer, including a human. Record a human review only after a human has performed it:

```sh
python3 scripts/fleet.py review FLEET-002 --author author-session-1 --reviewer human-owner --kind human --verdict pass
```

A fail verdict blocks readiness. The same reviewer can record a later pass after resolving findings. New commits invalidate old records. Update the branch when main has advanced, then repeat validation and review. Readiness also refuses dirty trees and branches with no new commit against main.

## Landing and hosting

The readiness result is advisory; it never merges, deploys, or authenticates reviewers. The pilot's human owner inspects the current revision and approves landing separately. GitHub publishing, required checks, and approval rules must be configured before claiming hosted enforcement; see `docs/policy.md`.

The initial test suite verifies ID validation, worktree creation, duplicate-card rejection, stale/self-review rejection, distinct protected-path reviewers, human review requirements, and unresolved failures. It does not establish the quality of a future product's tests.
