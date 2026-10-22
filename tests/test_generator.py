import json
from pathlib import Path
import tempfile
import unittest

from agent_dockerizer import detect, render


class GeneratorTests(unittest.TestCase):
    def test_node_detection_and_deterministic_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'package.json').write_text(json.dumps({'scripts': {'start': 'node index.js'}}))
            (root / 'package-lock.json').write_text('{"lockfileVersion": 3}')
            config = detect(root)
            self.assertEqual(config.stack, 'node')
            self.assertEqual(config.profile, 'generic')
            result = render(config)
            self.assertEqual(result, render(detect(root)))
            self.assertEqual(set(result), {'Dockerfile', 'compose.yaml', '.env.example', '.dockerignore', '.github/workflows/docker-build.yml'})
            self.assertIn('npm', result['Dockerfile'])


if __name__ == '__main__':
    unittest.main()
