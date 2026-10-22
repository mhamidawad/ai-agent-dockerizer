# Architecture
Python 3.11+ standard library; unittest; no external Python packages.
CLI callers: users, subprocess integration tests.
detect(project, entrypoint, profile) validates inputs; render(config) returns UTF-8 files; generate checks all destinations before writing.
Contracts: deterministic output; no environment/config values in output; no writes during dry-run; refuse existing outputs, symlink paths, ambiguous stacks, and unsafe entry points.
Reason for Depth: separate detection/rendering from output I/O so dry-run and generate share identical bytes and filesystem safety can be checked once.
Runtime images: node:22-bookworm-slim and python:3.12-slim [OK], maintained official images. Actions checkout@v4, setup-python@v5, login-action@v3, build-push-action@v6 [OK], maintained upstream actions. Version tags are mutable; digest pinning is deferred.
Limit: generated build excludes conventional secret paths, not arbitrary credentials embedded in source; no automatic secret discovery claim.
