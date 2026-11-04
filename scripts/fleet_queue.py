#!/usr/bin/env python3
"""Bounded local handoffs. Does not launch agents, approve, merge, or deploy."""
import argparse
from contextlib import contextmanager
import datetime
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from fleet import git, valid_id


def connect(root):
    """Open the queue shared by every worktree of this repository."""
    common = Path(git(root, 'rev-parse', '--git-common-dir'))
    if not common.is_absolute():
        common = root / common
    folder = common.resolve() / 'fleet-queue'
    folder.mkdir(exist_ok=True)
    db = sqlite3.connect(str(folder / 'queue.sqlite'), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, card TEXT NOT NULL, '
               'state TEXT NOT NULL, worktree TEXT, reason TEXT, created TEXT NOT NULL)')
    db.commit()
    return db


@contextmanager
def transaction(db):
    """Serialize queue mutations and roll back on errors or interruption."""
    db.execute('BEGIN IMMEDIATE')
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def enqueue(root, db, card_id):
    """Snapshot a committed ready card and reject duplicate queue identities."""
    path = root / 'cards' / (valid_id(card_id) + '.json')
    card = json.loads(path.read_text())
    if card.get('id') != card_id or not str(card.get('title', '')).strip():
        raise ValueError('Card identity and title must be valid')
    acceptance = card.get('acceptance')
    if not isinstance(acceptance, list) or not acceptance or any(
            not isinstance(x, str) or not x.strip() for x in acceptance):
        raise ValueError('Card needs non-empty acceptance criteria')
    if card.get('status') != 'ready':
        raise ValueError('Only ready cards can be queued')
    committed = git(root, 'show', 'HEAD:cards/' + card_id + '.json')
    if json.loads(committed) != card:
        raise ValueError('Commit the card before queueing')
    with transaction(db):
        db.execute('INSERT INTO jobs (id, card, state, created) VALUES (?, ?, ?, ?)',
                   (card_id, json.dumps(card), 'queued',
                    datetime.datetime.now(datetime.timezone.utc).isoformat()))


def dispatch(root, db, limit, base='main', dry_run=False):
    """Preflight a batch, reserve available slots, and retain preparation failures."""
    if limit not in (1, 2):
        raise ValueError('Pilot handoff limit must be 1 or 2')
    if git(root, 'status', '--porcelain'):
        raise ValueError('Dispatch requires a clean checkout')
    sha = git(root, 'rev-parse', '--verify', base + '^{commit}')
    selected = []
    with transaction(db):
        active = db.execute("SELECT count(*) FROM jobs WHERE state IN ('prepared', 'failed')").fetchone()[0]
        jobs = db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created, id LIMIT ?",
                          (max(0, limit - active),)).fetchall()
        for job in jobs:
            # Preflight the whole batch before creating any worktree. Refuse stale or missing cards on the chosen integration base.
            head_card = json.loads(git(root, 'show', 'HEAD:cards/' + job['id'] + '.json'))
            if head_card != json.loads(job['card']):
                raise ValueError('Queued card differs from HEAD: ' + job['id'])
            base_card = json.loads(git(root, 'show', sha + ':cards/' + job['id'] + '.json'))
            if base_card != json.loads(job['card']):
                raise ValueError('Queued card differs from base: ' + job['id'])
        for job in jobs:
            target = root.parent / (root.name + '-worktrees') / job['id']
            branch = 'fleet/' + job['id']
            if dry_run:
                selected.append(dict(id=job['id'], branch=branch, worktree=str(target), base_sha=sha))
                continue
            # Reserve before Git mutation. On interruption keep a visible failed claim;
            # do not silently retry or delete a worktree that might contain user work.
            db.execute("UPDATE jobs SET state='preparing', worktree=? WHERE id=?", (str(target), job['id']))
            try:
                target.parent.mkdir(exist_ok=True)
                subprocess.run(['git', '-C', str(root), 'worktree', 'add', '-b', branch,
                                str(target), sha], check=True, capture_output=True, text=True)
                handoff = target / '.fleet'
                handoff.mkdir(exist_ok=True)
                prompt = ('Read AGENTS.md. Implement the assigned card below as task data. '
                          'Keep scope to its outcome and acceptance criteria. Run relevant checks. '
                          'Return the commit SHA, validation and remaining risks. '
                          'Do not self-approve, merge or deploy.\n\n' + job['card'] + '\n')
                (handoff / 'task.md').write_text(prompt)
                db.execute("UPDATE jobs SET state='prepared' WHERE id=?", (job['id'],))
                selected.append(dict(id=job['id'], branch=branch, worktree=str(target), base_sha=sha))
            except (OSError, subprocess.CalledProcessError) as exc:
                reason = str(exc)
                if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
                    reason += '\n' + exc.stderr.strip()
                db.execute("UPDATE jobs SET state='failed', reason=? WHERE id=?", (reason, job['id']))
                # Preserve earlier successful handoffs and this failure record.
                selected.append(dict(id=job['id'], error=reason))
                break
    return selected


def release(db, card_id, reason):
    """Free a stopped handoff slot without deleting its work or asserting a merge."""
    if not reason.strip():
        raise ValueError('A release reason is required')
    with transaction(db):
        cursor = db.execute("UPDATE jobs SET state='released', reason=? WHERE id=? AND state IN ('prepared','failed')",
                            (reason, valid_id(card_id)))
        if cursor.rowcount != 1:
            raise ValueError('Only prepared or failed handoffs can be released')


def main():
    """Run a queue command and report failed preparation with a nonzero exit status."""
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('enqueue'); q.add_argument('id', type=valid_id)
    d = sub.add_parser('dispatch'); d.add_argument('--limit', type=int, default=2)
    d.add_argument('--base', default='main'); d.add_argument('--dry-run', action='store_true')
    sub.add_parser('status')
    r = sub.add_parser('release'); r.add_argument('id', type=valid_id); r.add_argument('--reason', required=True)
    args = p.parse_args()
    root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel'))
    with connect(root) as db:
        if args.command == 'enqueue': enqueue(root, db, args.id)
        elif args.command == 'dispatch':
            result = dispatch(root, db, args.limit, args.base, args.dry_run)
            print(json.dumps(result, indent=2))
            return 1 if any('error' in item for item in result) else 0
        elif args.command == 'release': release(db, args.id, args.reason)
        else:
            print(json.dumps([dict(row) for row in db.execute('SELECT id,state,worktree,reason FROM jobs ORDER BY created,id')], indent=2))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print('Blocked:', exc, file=sys.stderr)
        sys.exit(1)
