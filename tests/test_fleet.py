import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('fleet', Path(__file__).resolve().parents[1] / 'scripts/fleet.py')
fleet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fleet)


def review(reviewer='reviewer', sha='abc', verdict='pass', kind='agent'):
    return dict(author='author', reviewer=reviewer, sha=sha, verdict=verdict, kind=kind)


class PolicyTests(unittest.TestCase):
    def test_rejects_stale_review(self):
        self.assertTrue(fleet.review_errors([review(sha='old')], 'abc', 'author', False))

    def test_rejects_self_review(self):
        self.assertTrue(fleet.review_errors([review(reviewer='author')], 'abc', 'author', False))

    def test_requires_distinct_reviewers_and_human(self):
        self.assertTrue(fleet.review_errors([review(), review()], 'abc', 'author', True))
        self.assertTrue(fleet.review_errors([review(), review('second')], 'abc', 'author', True))
        self.assertFalse(fleet.review_errors([review(), review('owner', kind='human')], 'abc', 'author', True))

    def test_latest_verdict_supersedes_pass(self):
        self.assertTrue(fleet.review_errors([review(), review(verdict='fail')], 'abc', 'author', False))
        self.assertFalse(fleet.review_errors([review(verdict='fail'), review()], 'abc', 'author', False))

    def test_unresolved_failure_blocks_even_with_other_pass(self):
        self.assertTrue(fleet.review_errors([review(), review('other', verdict='fail')], 'abc', 'author', False))

    def test_protected_paths(self):
        self.assertTrue(fleet.protected(['scripts/fleet.py']))
        self.assertTrue(fleet.protected(['.github/workflows/ci.yml']))
        self.assertFalse(fleet.protected(['docs/quickstart.md']))

    def test_card_id_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            fleet.valid_id('../../outside')

    def test_card_to_worktree_integration(self):
        script = Path(fleet.__file__).resolve()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'repo'
            root.mkdir()
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True)
            def cli(*args):
                return subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True)
            git('init', '-b', 'main')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Fleet Test')
            self.assertEqual(cli('new', 'TEST-001', 'Task', '--accept', 'Works').returncode, 0)
            self.assertNotEqual(cli('new', 'TEST-001', 'Duplicate', '--accept', 'Works').returncode, 0)
            git('add', '.')
            git('commit', '-m', 'Card')
            result = cli('start', 'TEST-001')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root.parent / 'repo-worktrees' / 'TEST-001' / 'cards' / 'TEST-001.json').exists())
            self.assertNotEqual(cli('start', 'TEST-001').returncode, 0)


if __name__ == '__main__':
    unittest.main()
