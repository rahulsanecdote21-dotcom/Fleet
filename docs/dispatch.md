# Bounded local dispatch

This pilot prepares handoffs for a human to open in Codex. It does not launch subprocess agents, incur model charges, schedule tasks, post reviews, merge, or deploy. The limit bounds unreleased handoffs, not arbitrary Codex sessions a user might start separately.

Queue data lives in SQLite under the repository's common Git directory, shared by its worktrees. Queue claims are serialized with a database transaction. The pilot allows one or two active handoffs. Duplicate card IDs are rejected, including released IDs; create a new card for new work.

Commit a ready card on an intake branch (as in quickstart.md), then queue and dispatch against that branch:

```sh
python3 scripts/fleet_queue.py enqueue FLEET-003
python3 scripts/fleet_queue.py dispatch --base intake/FLEET-003 --dry-run
python3 scripts/fleet_queue.py dispatch --base intake/FLEET-003 --limit 2
python3 scripts/fleet_queue.py status
```

Use the printed worktree path and `.fleet/task.md` in a Codex session. The card must exist unchanged in both HEAD and the chosen base. Dispatch requires a clean checkout. Refresh the integration branch before intake; dispatch does not fetch GitHub or infer whether a local base is current. Do not also run fleet.py start for a queued card.

If a queued card changes or is deleted, cancel its old snapshot with `python3 scripts/fleet_queue.py cancel FLEET-003`. This removes only a queued entry, without touching files or branches. Correct and commit the card, then enqueue it again if needed. Prepared and failed handoffs cannot be cancelled; inspect and release them instead.

When the session is no longer active and its work is preserved:

```sh
python3 scripts/fleet_queue.py release FLEET-003 --reason 'Implementation preserved in PR; author session stopped'
```

Release frees a handoff slot. It does not assert that a change passed review, merged, or shipped, and it does not remove files or branches. Existing worktree/branch conflicts produce a failed entry for inspection rather than reusing or deleting another session's work.

After a process crash, inspect both queue status and `git worktree list` before retrying. SQLite rolls back interrupted transactions, but Git filesystem operations are not transactional with SQLite. A worktree created just before a crash may therefore remain without a recorded claim. Stop dispatch and reconcile that directory manually; never blindly remove it. This pilot is not a daemon, multi-machine scheduler, or hard spending cap. Unattended execution requires a separately configured runner, timeout, budget and recovery mechanism.
