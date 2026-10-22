import json
from pathlib import Path
import tempfile
import unittest

from agent_dockerizer import ProjectError, detect, render
from test_cli import cli


class SafetyTests(unittest.TestCase):
    def node(self, root):
        (root / 'package.json').write_text('{"scripts":{"start":"node index.js"}}')
        (root / 'package-lock.json').write_text('{"lockfileVersion":3}')

    def python(self, root):
        (root / 'requirements.txt').write_text('')
        (root / 'app.py').write_text('print("ready")')

    def test_unsupported_and_malformed_inputs_are_actionable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [
                ({}, 'No supported stack'),
                ({'package.json': '{'}, 'Invalid JSON'),
                ({'package.json': '[]'}, 'objects'),
                ({'package.json': '{}', 'package-lock.json': '{"lockfileVersion":3}'}, 'start script'),
                ({'package.json': '{"scripts":{"start":"npm start"}}'}, 'Invalid JSON'),
                ({'requirements.txt': ''}, '--entrypoint'),
                ({'requirements.txt': '', 'package.json': '{}'}, 'mixed stacks'),
            ]
            for files, message in cases:
                with self.subTest(message=message):
                    for p in root.iterdir():
                        p.unlink()
                    for name, content in files.items():
                        (root / name).write_text(content)
                    result = cli('dry-run', root)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)
                    self.assertEqual(result.stdout, '')

    def test_profile_ambiguity_and_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.node(root)
            (root / '.pi').mkdir()
            (root / '.opencode').mkdir()
            with self.assertRaisesRegex(ProjectError, 'multiple agent profiles'):
                detect(root)
            self.assertEqual(detect(root, profile='pi').profile, 'pi')
            with self.assertRaises(ProjectError):
                detect(root, profile='bad')

    def test_unsafe_python_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.python(root)
            for entry in ('../app.py', '/app.py', './app.py', 'a//app.py', 'a\\app.py', 'app.py\nRUN evil', 'missing.py', '-c', 'app.txt'):
                with self.subTest(entry=entry), self.assertRaises(ProjectError):
                    detect(root, entrypoint=entry)
            (root / 'nested').mkdir()
            (root / 'nested' / 'main.py').write_text('')
            self.assertIn('["python", "nested/main.py"]', render(detect(root, entrypoint='nested/main.py'))['Dockerfile'])

    def test_late_collision_does_not_partially_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.node(root)
            workflows = root / '.github' / 'workflows'
            workflows.mkdir(parents=True)
            existing = workflows / 'docker-build.yml'
            existing.write_text('keep me')
            result = cli('generate', root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(existing.read_text(), 'keep me')
            self.assertFalse((root / 'Dockerfile').exists())

    def test_output_symlinks_and_parent_files_are_rejected(self):
        for kind in ('directory-link', 'dangling-link', 'file-parent'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'project'
                outside = Path(tmp) / 'outside'
                root.mkdir()
                outside.mkdir()
                self.node(root)
                if kind == 'directory-link':
                    (root / '.github').symlink_to(outside, target_is_directory=True)
                elif kind == 'dangling-link':
                    (root / 'Dockerfile').symlink_to(outside / 'missing')
                else:
                    (root / '.github').write_text('keep')
                result = cli('generate', root)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(list(outside.iterdir()), [])
                self.assertFalse((root / 'compose.yaml').exists())

    def test_symlinked_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.python(root)
            (root / 'link.py').symlink_to(root / 'app.py')
            with self.assertRaisesRegex(ProjectError, 'Symlinked'):
                detect(root, entrypoint='link.py')
            (root / 'requirements.txt').unlink()
            (root / 'requirements.txt').symlink_to(root / 'app.py')
            with self.assertRaisesRegex(ProjectError, 'Symlinked'):
                detect(root, entrypoint='app.py')

    def test_option_like_python_filename_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.python(root)
            (root / '-danger.py').write_text('')
            with self.assertRaises(ProjectError):
                detect(root, entrypoint='-danger.py')

    def test_symlinked_project_ancestor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / 'real' / 'project'
            project.mkdir(parents=True)
            self.node(project)
            (base / 'link').symlink_to(base / 'real', target_is_directory=True)
            result = cli('generate', base / 'link' / 'project')
            self.assertEqual(result.returncode, 2)
            self.assertFalse((project / 'Dockerfile').exists())

    def test_manifest_values_do_not_enter_preview_or_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.node(root)
            sentinel = 'synthetic-manifest-secret-DO-NOT-COPY'
            (root / 'package.json').write_text(json.dumps({'name': sentinel, 'scripts': {'start': 'echo ' + sentinel}, 'apiKey': sentinel}))
            result = cli('dry-run', root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(sentinel, result.stdout + result.stderr)
            (root / 'package.json').write_text(sentinel)
            result = cli('dry-run', root)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(sentinel, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
