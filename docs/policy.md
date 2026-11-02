# Operating policy and activation checklist

## Pilot

Use one card per change and start with two concurrent authors. Keep changes small enough to explain and review. An independent reviewer checks the current SHA; protected paths require two independent reviewers including a human. Human landing remains the default. Review outage means pause or use an explicitly appointed independent human fallback, never bypass review.

The local CLI offers advisory checks only. Before hosted enforcement:
- Choose the GitHub repository, owners, authenticated reviewer identities, and spending limit.
- Enable required PRs, forbid force-push/deletion of main, and restrict bypass privileges.
- Require the starter's `test` check; replace/extend it with product lint, type, unit, integration, and build checks once a product exists.
- Require current-commit approvals with stale-review dismissal and approval of the latest push; define actual protected directories and human owners.
- Ensure protected-path review count is enforced by supported rulesets or a separately trusted GitHub App. CODEOWNERS alone does not enforce two distinct reviews for selected paths.
- Enable automatic Codex review if available. Do not equate a bot comment or absence of findings with an authenticated passing verdict.
- Use merge queue only if supported and needed; retain `merge_group` CI coverage. Do not batch or replace source control before measuring a bottleneck.
- Run the full applicable suite on main. A failed main check pauses landing and creates a triage task. Confirm reproducibility on the exact suspected commit before proposing a revert; a human approves any revert during the pilot.
- Define a separate release environment and promotion authorization when a deployable application exists.

## Measure before scaling

Record UTC timestamps for card accepted, PR opened, latest push, final valid approval, and merge. Report PR-open-to-merge and final-approval-to-merge separately. Invalidated approvals do not count. Define one land as a merged PR under a fixed merge strategy; raw first-parent commit counts include direct pushes and cannot be assumed equivalent to PRs.

Track changed files/lines, escaped defects, incidents, reverts attributable to landed changes, review rounds, CI minutes, queue cancellations, agent/reviewer cost, and missing data. Report the denominator, observation window, and unavailable values. Never use Goliath's rates as local performance targets.

## Nightly loop (prepared, not scheduled)

Use docs/prompts.md after real activity exists. Read evidence and rank failure classes by time and cost. Propose cards; do not auto-approve, merge, change guards, handle secrets, or promote releases. Notify on actionable findings only. Shadow candidate CI/reviewer changes against a representative adjudicated sample; assess missed bugs and false blocks, not agreement alone. Activation needs repository context, a schedule, review provider, and cost limit.
