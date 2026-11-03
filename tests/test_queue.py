import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fleet_queue as queue


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Queue Test')
        (self.root / '.gitignore').write_text('.fleet/\n')
        (self.root / 'cards').mkdir()
        for i in range(1, 4):
            card = dict(id=f'TEST-00{i}', title='Task', acceptance=['Works'], status='ready')
            (self.root / 'cards' / (card['id'] + '.json')).write_text(json.dumps(card))
        self.git('add', '.')
        self.git('commit', '-m', 'Initial cards')
        self.db = queue.connect(self.root)
        self.addCleanup(self.db.close)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.DEVNULL).strip()

    def test_duplicate_claim_and_validation(self):
        queue.enqueue(self.root, self.db, 'TEST-001')
        with self.assertRaises(sqlite3.IntegrityError):
            queue.enqueue(self.root, self.db, 'TEST-001')
        path = self.root / 'cards/TEST-002.json'
        card = json.loads(path.read_text()); card['acceptance'] = []
        path.write_text(json.dumps(card))
        with self.assertRaises(ValueError):
            queue.enqueue(self.root, self.db, 'TEST-002')

    def test_dry_run_is_non_mutating(self):
        queue.enqueue(self.root, self.db, 'TEST-001')
        result = queue.dispatch(self.root, self.db, 2, dry_run=True)
        self.assertEqual(len(result), 1)
        self.assertFalse(Path(result[0]['worktree']).exists())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'queued')

    def test_dispatch_bounds_handoffs_and_releases(self):
        for i in range(1, 4): queue.enqueue(self.root, self.db, f'TEST-00{i}')
        result = queue.dispatch(self.root, self.db, 2)
        self.assertEqual(len(result), 2)
        self.assertTrue((Path(result[0]['worktree']) / '.fleet/task.md').exists())
        self.assertEqual(queue.dispatch(self.root, self.db, 2), [])
        # A connection from a worktree sees the same reservations.
        other = queue.connect(Path(result[0]['worktree']))
        try:
            self.assertEqual(other.execute("SELECT count(*) FROM jobs WHERE state='prepared'").fetchone()[0], 2)
        finally: other.close()
        queue.release(self.db, 'TEST-001', 'Session stopped, work preserved')
        self.assertEqual(queue.dispatch(self.root, self.db, 2)[0]['id'], 'TEST-003')

    def test_conflicting_branch_preserves_failure(self):
        queue.enqueue(self.root, self.db, 'TEST-001')
        self.git('branch', 'fleet/TEST-001')
        result = queue.dispatch(self.root, self.db, 2)
        self.assertIn('error', result[0])
        self.assertIn('already exists', result[0]['error'])
        self.assertIn('already exists', self.db.execute('SELECT reason FROM jobs').fetchone()[0])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'failed')


    def test_parent_creation_failure_is_retained(self):
        queue.enqueue(self.root, self.db, 'TEST-001')
        (self.root.parent / 'repo-worktrees').write_text('Occupied by a file')
        result = queue.dispatch(self.root, self.db, 2)
        self.assertIn('error', result[0])
        row = self.db.execute('SELECT state,reason FROM jobs').fetchone()
        self.assertEqual(row['state'], 'failed')
        self.assertTrue(row['reason'])

    def test_cli_dispatch_failure_returns_nonzero_with_json(self):
        queue.enqueue(self.root, self.db, 'TEST-001')
        self.git('branch', 'fleet/TEST-001')
        result = subprocess.run([sys.executable, str(Path(queue.__file__).resolve()), 'dispatch'],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn('already exists', payload[0]['error'])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'failed')

    def test_dirty_tree_and_invalid_limits_rejected(self):
        with self.assertRaises(ValueError): queue.dispatch(self.root, self.db, 3)
        (self.root / 'uncommitted').write_text('dirty')
        with self.assertRaises(ValueError): queue.dispatch(self.root, self.db, 2)

    def test_batch_preflight_prevents_partial_worktrees(self):
        queue.enqueue(self.root, self.db, 'TEST-001')
        queue.enqueue(self.root, self.db, 'TEST-002')
        self.db.execute("UPDATE jobs SET card=? WHERE id='TEST-002'", (json.dumps(dict(id='TEST-002', title='Changed')),))
        self.db.commit()
        with self.assertRaises(ValueError): queue.dispatch(self.root, self.db, 2)
        self.assertFalse((self.root.parent / 'repo-worktrees/TEST-001').exists())
        self.assertEqual(self.db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0], 2)


if __name__ == '__main__': unittest.main()
