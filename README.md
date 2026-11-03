# Codex Fleet

A working local starter for card → isolated worktree → implementation → independent review → checks → human landing. Created 1 November 2026 from a critical review of the Goliath brief.

## Ready now

- Python standard-library CLI for creating cards and isolated Git worktrees.
- Local SHA-bound review records and a readiness check that rejects stale evidence, self-review, dirty trees, and insufficient protected-path review.
- Agent instructions, issue and PR templates, CI for this starter, and a staged operating policy.
- A pilot card for the first end-to-end exercise.
- Bounded local handoff preparation with a shared SQLite queue; see `docs/dispatch.md`.

The starter is hosted at https://github.com/rahulsanecdote21-dotcom/Fleet. Its main branch requires PRs, the passing test check on an up-to-date branch, resolved conversations, and fresh independent approval of the latest push, including for administrators. An unattended agent executor, nightly schedule, deployment, and automatic revert are not active. The local queue prepares worktrees and prompts without launching agents. CodeRabbit review is installed for this repository; automatic approval excludes protected paths. Local evidence can be edited by the user and is not a security boundary. CI verifies the starter's tests; it does not yet verify the code of a future product.

## First run

```sh
python3 -m unittest discover -s tests -v
python3 scripts/fleet.py list
git worktree list
```

The original setup already created the pilot branch and worktree. Fresh clones do not inherit local worktrees. See docs/quickstart.md before creating one. The start command uses a sibling directory named after the checkout and does not launch or charge an agent. Open that worktree in Codex and use the prompt in `docs/prompts.md`. Start with at most two authoring sessions so review capacity can keep up. Alternatively, use the app's Worktree mode for a new card; do not create both kinds of worktree for the same card.

## Add a task

```sh
git switch main
git pull --ff-only origin main
git switch -c intake/FLEET-003
python3 scripts/fleet.py new FLEET-003 'Describe the requested result' --accept 'State a verifiable acceptance criterion'
git add cards/FLEET-003.json
git commit -m 'Add FLEET-003 card'
python3 scripts/fleet.py start FLEET-003
```

Commit a card on the local intake branch before starting it. The implementation branch includes that card commit; submit it together with the implementation as one PR. Do not commit directly to protected main. Worktrees start from the current HEAD, so commit setup changes first. Existing dirty files are never copied into a new worktree. Use `git worktree list` to inspect worktrees; remove completed ones with Git only after preserving their commits and confirming they have no needed changes.

## Review the implementation

After the author commits, run these inside its worktree. Replace the example identities with real distinct session or human identities. A pass may be recorded only after an actual independent review.

```sh
python3 scripts/fleet.py review FLEET-001 --author author-session-1 --reviewer reviewer-session-2 --kind agent --verdict pass
python3 scripts/fleet.py review FLEET-001 --author author-session-1 --reviewer human-owner --kind human --verdict pass
python3 scripts/fleet.py ready FLEET-001 --author author-session-1 --base main
```

Review records live under `.fleet/` in that worktree and are ignored by Git. Readiness checks the current committed SHA and runs the test suite. A new push/commit needs fresh review. A failed review supersedes that reviewer's prior pass. The base must be an ancestor of HEAD; when main advances, update the branch and repeat checks/review. This conservatively avoids validating an obsolete integration tree.

## Hosted workflow

The repository is published at https://github.com/rahulsanecdote21-dotcom/Fleet. The `test` check is required on main, with current-commit independent approval and stale-review dismissal. The PR author cannot provide their own required GitHub approval. Local agent review records do not replace that approval. CI and issue/PR templates are active; automated Codex review and path-specific two-reviewer enforcement remain to be configured. Forks and new repositories must configure their own rules from docs/policy.md.

See `docs/review.md` for the brief assessment, `docs/policy.md` for rollout and metrics, and `docs/prompts.md` for author/reviewer/nightly prompts.
