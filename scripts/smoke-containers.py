"""Optional Docker integration smoke; uses only synthetic fixture projects.

Run: python3 scripts/smoke-containers.py
Requires a running Docker daemon and network access for official base images.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def main():
    tags = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for stack in ('node', 'python'):
                for profile in ('generic', 'pi', 'opencode'):
                    case = f'{stack}-{profile}'
                    root = Path(tmp) / case
                    shutil.copytree(REPO / 'tests' / 'fixtures' / case, root)
                    options = ['--entrypoint', 'app.py'] if stack == 'python' else []
                    run([sys.executable, '-m', 'agent_dockerizer', 'generate', str(root), *options], cwd=REPO)
                    run(['docker', 'compose', '-f', str(root / 'compose.yaml'), 'config', '--quiet'])
                    print(f'PASS Compose: {case}', flush=True)
                    if profile != 'generic':
                        continue
                    # Add real files at all excluded paths so absence in the image
                    # proves exclusion rather than just absence from the fixture.
                    for marker in ('.pi', '.opencode'):
                        (root / marker).mkdir()
                        (root / marker / 'settings.json').write_text('{"apiKey":"synthetic-build-context-secret"}')
                    tag = f'agent-dockerizer-smoke-{os.getpid()}:{stack}'
                    tags.append(tag)
                    run(['docker', 'build', '--quiet', '-t', tag, str(root)], timeout=180)
                    result = run(['docker', 'run', '--rm', tag], timeout=30)
                    # npm start also prints a package/script banner before app output.
                    if not result.stdout.splitlines() or result.stdout.splitlines()[-1] != 'agent ready':
                        raise RuntimeError('Container entrypoint did not produce expected fixture output')
                    run(['docker', 'run', '--rm', '--entrypoint', 'sh', tag, '-c',
                         'test "$(id -u)" != 0 && test ! -e /app/.env && test ! -e /app/.pi && test ! -e /app/.opencode'], timeout=30)
                    print(f'PASS Build/run/non-root/secret exclusion: {stack}', flush=True)
    finally:
        for tag in tags:
            subprocess.run(['docker', 'image', 'rm', tag], capture_output=True)


if __name__ == '__main__':
    main()
