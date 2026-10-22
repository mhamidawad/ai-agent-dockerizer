"""Deterministic container artifacts for small agent projects (standard library only)."""
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath


class ProjectError(ValueError):
    """An unsupported input, reported without including project values."""


@dataclass(frozen=True)
class Config:
    stack: str
    profile: str
    entrypoint: str | None = None


def _file(root: Path, name: str) -> Path:
    path = root / name
    if path.is_symlink():
        raise ProjectError('Symlinked project inputs are unsupported; use regular files.')
    return path


def _json(root: Path, name: str) -> dict:
    try:
        value = json.loads(_file(root, name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ProjectError('Invalid JSON manifest; supply valid package.json and package-lock.json.') from None
    if not isinstance(value, dict):
        raise ProjectError('JSON manifests must contain objects.')
    return value


def detect(project: Path, *, entrypoint: str | None = None, profile: str | None = None) -> Config:
    """Validate a supported project without reading environment or agent config values."""
    root = Path(project)
    if not root.is_dir():
        raise ProjectError('Project directory not found; supply an existing directory.')
    node = _file(root, 'package.json').is_file()
    python = _file(root, 'requirements.txt').is_file()
    if node and python:
        raise ProjectError('Detected Node and Python manifests; mixed stacks are unsupported. Use a single-stack project directory.')
    if not node and not python:
        raise ProjectError('No supported stack detected; add package.json/package-lock.json or requirements.txt with --entrypoint app.py.')
    if profile is not None and profile not in ('generic', 'pi', 'opencode'):
        raise ProjectError('Unsupported profile; choose generic, pi, or opencode.')
    if profile is None:
        markers = [name for name in ('pi', 'opencode') if (root / ('.' + name)).exists()]
        if len(markers) > 1:
            raise ProjectError('Detected multiple agent profiles; select --profile generic, pi, or opencode.')
        profile = markers[0] if markers else 'generic'
    if node:
        package = _json(root, 'package.json')
        lock = _json(root, 'package-lock.json')
        scripts = package.get('scripts')
        if not isinstance(scripts, dict) or not isinstance(scripts.get('start'), str) or not scripts['start'].strip():
            raise ProjectError('Detected Node project without a start script; add scripts.start to package.json.')
        if lock.get('lockfileVersion') not in (1, 2, 3):
            raise ProjectError('Detected unsupported npm lockfile; regenerate package-lock.json with npm.')
        if entrypoint is not None:
            raise ProjectError('Detected Node project; omit --entrypoint and use npm start.')
        return Config('node', profile)
    if not entrypoint:
        raise ProjectError('Detected Python project; provide --entrypoint with a relative .py file, for example app.py.')
    parts = PurePosixPath(entrypoint)
    if (parts.is_absolute() or '\\' in entrypoint or any(part in ('', '.', '..') for part in entrypoint.split('/'))
            or not entrypoint.endswith('.py') or any(not (c.isalnum() or c in '_-./') or not c.isascii() for c in entrypoint)):
        raise ProjectError('Unsafe Python entry point; use a relative .py path with letters, digits, underscores, hyphens and slashes.')
    current = root
    for part in parts.parts:
        current = _file(current, part)
    if not current.is_file():
        raise ProjectError('Python entry point not found; supply an existing relative .py file.')
    return Config('python', profile, entrypoint)


DOCKERIGNORE = '''.git
.github
.env
.env.*
*.env
*.pem
*.key
.ssh
.aws
.pi
.opencode
node_modules
.venv
venv
__pycache__
*.pyc
tests
specs
Dockerfile
compose.yaml
'''

WORKFLOW = '''name: Container build
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Set lowercase image name
        id: image
        run: echo "name=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"
      - name: Log in to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and optionally publish
        uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.image.outputs.name }}:latest
'''


def render(config: Config) -> dict[str, str]:
    """Render fixed templates. No project values other than a validated entry point enter output."""
    if config.stack == 'node':
        dockerfile = '''FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY --chown=node:node . .
USER node
CMD ["npm", "start"]
'''
    elif config.stack == 'python':
        dockerfile = '''FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 app
COPY --chown=app:app . .
USER app
CMD ''' + json.dumps(['python', config.entrypoint]) + '\n'
    else:
        raise ProjectError('Unsupported stack; use detect() to obtain a validated configuration.')
    return {
        'Dockerfile': dockerfile,
        'compose.yaml': '''services:
  agent:
    build: .
    env_file: .env
    init: true
    stdin_open: true
    tty: true
    labels:
      ai.agent.profile: ''' + config.profile + '\n',
        '.env.example': '# Copy to .env and fill in only the providers you use. Never commit .env.\nOPENAI_API_KEY=\nANTHROPIC_API_KEY=\n',
        '.dockerignore': DOCKERIGNORE,
        '.github/workflows/docker-build.yml': WORKFLOW,
    }
