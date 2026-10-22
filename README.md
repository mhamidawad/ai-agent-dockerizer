# Agent Dockerizer

Generate Docker and Compose files and a GitHub Actions GHCR build workflow
for small Node.js or Python agent projects. Requires Python 3.11+ on the host.
The CLI has no third-party Python dependencies and does not require installation.

## Try it

From this repository, preview an included fixture without changing it:

```sh
python3 -m agent_dockerizer dry-run tests/fixtures/node-pi
```

Generate files in **your project**, from this repository directory:

```sh
python3 -m agent_dockerizer dry-run /path/to/project
python3 -m agent_dockerizer generate /path/to/project
```

For Python projects, add `--entrypoint app.py` to both commands.
Preview writes a JSON map of filenames to contents. Generation refuses to
overwrite any of its five output files. Move existing outputs aside first;
there is no force flag. Keep the project directory unchanged during generation.

## Supported inputs

| Stack | Required input | Container command |
| --- | --- | --- |
| Node.js | `package.json` with `scripts.start`, matching `package-lock.json` (v1–v3) | `npm start` |
| Python | `requirements.txt`, explicit existing relative `.py` entry point | `python app.py` |

A project with both manifests is rejected; point the CLI at a single-stack
subdirectory instead. Lockfile/package consistency is checked by npm at image
build time. npm lifecycle install scripts are disabled; packages that need
native compilation or postinstall steps need manual Dockerfile changes.
Python dependencies must be available to pip; there is no Poetry/uv support.

Profiles are `generic`, `pi`, and `opencode`. A `.pi` or `.opencode` path
selects that profile. Without either marker, the profile is generic.
Use `--profile pi` (or another supported value) to override detection,
including when both markers exist. Profiles are metadata labels, **not**
installers for the Pi/OpenCode CLIs. Your npm start script or Python entry
point must launch your application and declare its own dependencies.

## Generated output

- `Dockerfile`: Node 22 or Python 3.12, non-root runtime user.
- `compose.yaml`: builds locally; loads runtime variables from `.env`.
- `.env.example`: empty provider-key placeholders, never detected values.
- `.dockerignore`: excludes conventional secret paths, agent settings, VCS
  data, and local dependencies from the build context.
- `.github/workflows/docker-build.yml`: builds on PRs; builds and publishes
  to `ghcr.io/owner/repo:latest` on main pushes or manual runs.

After generation, in your project directory:

```sh
cp .env.example .env
# Edit .env privately. Add .env and other credentials to your .gitignore.
docker compose config --quiet
docker compose run --rm agent
```

Commit the generated files (not `.env`) to your project's GitHub repository
and push to main to run the build workflow. The workflow uses GITHUB_TOKEN,
not credentials from your local environment. GHCR publishing needs repository
Actions/package permissions. Organization policies may require further setup.
No remote builds or publishing are performed by the generator itself.

## Security and limits

The generator never reads `.env` or agent configuration contents, never runs
project scripts, and never embeds manifest values in templates. It checks all
output paths before writing, rejects symlink inputs/destinations, uses exclusive
file creation, and rolls back created files after I/O errors. Do not concurrently
modify the project while generating.

Ignore rules cover conventional credential files; they cannot identify secrets
embedded in arbitrary source or dependency files. Inspect the build context
before building. Dependency installs and application start commands execute
project-controlled code **inside the build/runtime container**; use trusted
projects. There is no automatic secret scan, sandbox, deployment, exposed port,
or promise that every arbitrary agent project will build unchanged.
Runtime images and action references use mutable version tags, not digests.

## Tests

```sh
python3 -m unittest discover -s tests -v
bash scripts/lib/plan-consistency-check.sh specs/epics/e01-generator
```

Tests use only the standard library and do not need Docker or network access.
CI runs the same test command on Python 3.11, 3.12, and 3.13. Six fixture
directories cover the complete stack/profile matrix. Goldens cover all five
generated files; normal tests never regenerate them. Fake fixture credentials
are intentional test data, not usable keys.

To change expected output, review the template change, manually update only
the affected files in `tests/golden/`, and rerun the tests. Do not replace the
goldens with newly generated output without reviewing the diff.

## Status

This is a greenfield bootstrap, not evidence that the historical launch and
release items in PLAN.md occurred. See `specs/verifications/e01s01.md` for
local verification and any pending remote CI evidence.
