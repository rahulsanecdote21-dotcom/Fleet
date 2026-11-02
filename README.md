# Codex Fleet

A working local starter for card → isolated worktree → implementation → independent review → checks → human landing. Created 1 November 2026 from a critical review of the Goliath brief.

## Ready now

- Python standard-library CLI for creating cards and isolated Git worktrees.
- Local SHA-bound review records and a readiness check that rejects stale evidence, self-review, dirty trees, and insufficient protected-path review.
- Agent instructions, issue and PR templates, CI for this starter, and a staged operating policy.
- A pilot card for the first end-to-end exercise.

This is a new local Git repository. No GitHub remote, hosted branch protection, agent dispatcher, paid reviewer integration, nightly schedule, deployment, or automatic revert is active. Local evidence can be edited by the user and is not a security boundary. CI verifies the starter's tests; it does not yet verify the code of a future product.

## First run

```sh
python3 -m unittest discover -s tests -v
python3 scripts/fleet.py list
python3 scripts/fleet.py start FLEET-001
```

The last command creates branch `fleet/FLEET-001` in the sibling folder `codex-fleet-worktrees/FLEET-001`. It does not launch or charge an agent. Open that worktree in Codex and use the prompt in `docs/prompts.md`. Start with at most two authoring sessions so review capacity can keep up. Alternatively, use the app's Worktree mode for a new card; do not create both kinds of worktree for the same card.

## Add a task

```sh
python3 scripts/fleet.py new FLEET-002 'Describe the requested result' --accept 'State a verifiable acceptance criterion'
git add cards/FLEET-002.json
git commit -m 'Add FLEET-002 card'
python3 scripts/fleet.py start FLEET-002
```

Commit a card before starting it. Worktrees start from the current HEAD, so commit setup changes first. Existing dirty files are never copied into a new worktree. Use `git worktree list` to inspect worktrees; remove completed ones with Git only after preserving their commits and confirming they have no needed changes.

## Review the implementation

After the author commits, run these inside its worktree. Replace the example identities with real distinct session or human identities. A pass may be recorded only after an actual independent review.

```sh
python3 scripts/fleet.py review FLEET-001 --author author-session-1 --reviewer reviewer-session-2 --kind agent --verdict pass
python3 scripts/fleet.py review FLEET-001 --author author-session-1 --reviewer human-owner --kind human --verdict pass
python3 scripts/fleet.py ready FLEET-001 --author author-session-1 --base main
```

Review records live under `.fleet/` in that worktree and are ignored by Git. Readiness checks the current committed SHA and runs the test suite. A new push/commit needs fresh review. A failed review supersedes that reviewer's prior pass. The base must be an ancestor of HEAD; when main advances, update the branch and repeat checks/review. This conservatively avoids validating an obsolete integration tree.

## Connect GitHub later

Create an empty remote, add it as `origin`, and push `main` after reviewing these files. Enable the repository's Codex review integration if available, then configure the controls in `docs/policy.md`. The included GitHub issue form and CI workflow take effect after push. Set GitHub rules to require the `test` check and stale-review dismissal; do not assume the workflow alone blocks merging.

See `docs/review.md` for the brief assessment, `docs/policy.md` for rollout and metrics, and `docs/prompts.md` for author/reviewer/nightly prompts.
