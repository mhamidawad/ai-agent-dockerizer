"""Goldens are literal reviewed fixtures; tests never update expected output."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from agent_dockerizer import detect, render
from test_cli import cli

BASE = Path(__file__).parent
ARTIFACTS = {'Dockerfile', 'compose.yaml', '.env.example', '.dockerignore', '.github/workflows/docker-build.yml'}
SENTINELS = ('fixture-env-secret-DO-NOT-COPY', 'fixture-config-secret-DO-NOT-COPY')


class GoldenTests(unittest.TestCase):
    def test_all_supported_combinations(self):
        for stack in ('node', 'python'):
            for profile in ('generic', 'pi', 'opencode'):
                case = f'{stack}-{profile}'
                with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp) / 'project'
                    shutil.copytree(BASE / 'fixtures' / case, root)
                    options = ['--entrypoint', 'app.py'] if stack == 'python' else []
                    config = detect(root, entrypoint='app.py' if stack == 'python' else None)
                    self.assertEqual((config.stack, config.profile), (stack, profile))
                    expected_root = BASE / 'golden' / case
                    expected = {p.relative_to(expected_root).as_posix(): p.read_bytes() for p in expected_root.rglob('*') if p.is_file()}
                    self.assertEqual(set(expected), ARTIFACTS)
                    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
                    first = cli('dry-run', root, *options)
                    second = cli('dry-run', root, *options)
                    self.assertEqual(first.returncode, 0, first.stderr)
                    self.assertEqual(second.returncode, 0, second.stderr)
                    self.assertEqual(first.stdout, second.stdout)
                    self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()})
                    preview = json.loads(first.stdout)
                    self.assertEqual({name: content.encode() for name, content in preview.items()}, expected)
                    self.assertEqual({name: content.encode() for name, content in render(config).items()}, expected)
                    result = cli('generate', root, *options)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for name, content in expected.items():
                        self.assertEqual((root / name).read_bytes(), content)
                    output = first.stdout + first.stderr + second.stdout + second.stderr + result.stdout + result.stderr + ''.join(preview.values())
                    for sentinel in SENTINELS:
                        self.assertNotIn(sentinel, output)
                    # Generate independently into a different absolute path too.
                    other = Path(tmp) / 'other'
                    shutil.copytree(BASE / 'fixtures' / case, other)
                    result = cli('generate', other, *options)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for name, content in expected.items():
                        self.assertEqual((other / name).read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
