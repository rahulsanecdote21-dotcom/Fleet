#!/usr/bin/env python3
"""Local workflow helper. Review records are advisory, not authenticated gates."""
import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def valid_id(value):
    if not re.fullmatch(r'[A-Z][A-Z0-9]*-[0-9]+', value):
        raise ValueError('Card ID must look like FLEET-001')
    return value


def protected(paths):
    return any(p in ('AGENTS.md', 'docs/policy.md') or
               p.startswith(('.github/', 'auth/', 'billing/', 'migrations/', 'scripts/'))
               for p in paths)


def review_errors(records, sha, author, sensitive):
    latest = {}
    for record in records:
        if record['sha'] == sha:
            latest[record['reviewer']] = record
    independent = [r for r in latest.values()
                   if r['reviewer'] != author and r['author'] == author]
    errors = []
    if any(r['verdict'] == 'fail' for r in independent):
        errors.append('An independent reviewer still has blocking findings')
    passes = [r for r in independent if r['verdict'] == 'pass']
    if len(passes) < (2 if sensitive else 1):
        errors.append('Insufficient independent reviews for the current SHA')
    if sensitive and not any(r['kind'] == 'human' for r in passes):
        errors.append('Protected paths require a human review')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    new = sub.add_parser('new')
    new.add_argument('id', type=valid_id)
    new.add_argument('title')
    new.add_argument('--accept', action='append', required=True)
    start = sub.add_parser('start')
    start.add_argument('id', type=valid_id)
    review = sub.add_parser('review')
    review.add_argument('id', type=valid_id)
    review.add_argument('--author', required=True)
    review.add_argument('--reviewer', required=True)
    review.add_argument('--kind', choices=['agent', 'human'], required=True)
    review.add_argument('--verdict', choices=['pass', 'fail'], required=True)
    ready = sub.add_parser('ready')
    ready.add_argument('id', type=valid_id)
    ready.add_argument('--author', required=True)
    ready.add_argument('--base', default='main')
    args = parser.parse_args()
    root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel'))
    if args.command == 'list':
        for path in sorted((root / 'cards').glob('*.json')):
            card = json.loads(path.read_text())
            print(f"{card['id']} [{card['status']}] {card['title']}")
        return
    path = root / 'cards' / (args.id + '.json')
    if args.command == 'new':
        if not args.title.strip() or any(not x.strip() for x in args.accept):
            raise ValueError('Title and acceptance criteria cannot be empty')
        path.parent.mkdir(exist_ok=True)
        with path.open('x') as f:
            json.dump(dict(id=args.id, title=args.title, acceptance=args.accept, status='ready'), f, indent=2)
            f.write('\n')
        print(path)
        return
    if not path.exists():
        raise ValueError('Create the card first')
    if args.command == 'start':
        if git(root, 'status', '--porcelain'):
            raise ValueError('Commit or preserve current changes before creating a worktree')
        target = root.parent / (root.name + '-worktrees') / args.id
        target.parent.mkdir(exist_ok=True)
        subprocess.run(['git', '-C', str(root), 'worktree', 'add', '-b',
                        'fleet/' + args.id, str(target), 'HEAD'], check=True)
        print('Open in Codex:', target)
        return
    if git(root, 'branch', '--show-current') != 'fleet/' + args.id:
        raise ValueError('Run this command on the card branch fleet/' + args.id)
    sha = git(root, 'rev-parse', 'HEAD')
    evidence = root / '.fleet' / (args.id + '.json')
    records = json.loads(evidence.read_text()) if evidence.exists() else []
    if not args.author.strip():
        raise ValueError('Author identity cannot be empty')
    if args.command == 'review':
        if not args.reviewer.strip() or args.author == args.reviewer:
            raise ValueError('Reviewer must be independent of the author')
        if git(root, 'status', '--porcelain'):
            raise ValueError('Commit changes before recording an exact-SHA review')
        records.append(dict(sha=sha, author=args.author, reviewer=args.reviewer,
                            kind=args.kind, verdict=args.verdict,
                            at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text(json.dumps(records, indent=2) + '\n')
        print('Recorded advisory review for', sha)
        return
    if git(root, 'status', '--porcelain'):
        raise ValueError('Working tree is dirty')
    base = git(root, 'rev-parse', '--verify', args.base + '^{commit}')
    if git(root, 'merge-base', base, sha) != base:
        raise ValueError('Base advanced or diverged: update the branch, then recheck/review')
    if base == sha:
        raise ValueError('No committed change against base')
    paths = git(root, 'diff', '--name-only', base, sha).splitlines()
    errors = review_errors(records, sha, args.author, protected(paths))
    if errors:
        raise ValueError('; '.join(errors))
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root, check=True)
    print('Advisory readiness passed for', sha)
    print('Hosted required checks, authenticated approvals, and human landing still apply.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('Blocked:', exc, file=sys.stderr)
        sys.exit(1)
