import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_dockerizer import detect, render
from agent_dockerizer.__main__ import generate

REPO = Path(__file__).resolve().parents[1]


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'agent_dockerizer', *map(str, args)], cwd=REPO, capture_output=True, text=True)


class CliTests(unittest.TestCase):
    def make_project(self, root):
        (root / 'requirements.txt').write_text('')
        (root / 'app.py').write_text('print("hello")\n')
        (root / '.env').write_text('OPENAI_API_KEY=fixture-not-a-real-secret\n')

    def test_io_failure_rolls_back_only_generated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            (root / '.github').mkdir()
            before = {p.relative_to(root) for p in root.rglob('*')}
            original_open = Path.open

            def fail_on_workflow(path, *args, **kwargs):
                if path.name == 'docker-build.yml':
                    raise PermissionError('simulated write failure')
                return original_open(path, *args, **kwargs)

            outputs = render(detect(root, entrypoint='app.py'))
            with patch.object(Path, 'open', fail_on_workflow), self.assertRaises(PermissionError):
                generate(root, outputs)
            self.assertEqual(before, {p.relative_to(root) for p in root.rglob('*')})
            self.assertEqual((root / 'app.py').read_text(), 'print("hello")\n')

    def test_dry_run_and_generate_same_bytes_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            before = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
            preview = cli('dry-run', root, '--entrypoint', 'app.py')
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob('*')))
            outputs = json.loads(preview.stdout)
            generated = cli('generate', root, '--entrypoint', 'app.py')
            self.assertEqual(generated.returncode, 0, generated.stderr)
            for name, content in outputs.items():
                self.assertEqual((root / name).read_bytes(), content.encode())
            self.assertNotIn('fixture-not-a-real-secret', preview.stdout + preview.stderr + generated.stdout + generated.stderr)
            again = cli('generate', root, '--entrypoint', 'app.py')
            self.assertNotEqual(again.returncode, 0)
            self.assertIn('existing', again.stderr.lower())
            for name, content in outputs.items():
                self.assertEqual((root / name).read_bytes(), content.encode())


if __name__ == '__main__':
    unittest.main()
