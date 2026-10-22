# PLAN.md (Pi version)

## Goal
Take the Docker/Compose/GitHub Actions generator for agent projects from v0.1.0
to v0.2.0 using real user feedback.
North-star: a new user goes from `dry-run` to a green CI build in under 10 minutes.

## How to work (read first)
- Do ONE unchecked task per turn, in order. Don't skip ahead.
- Before editing: state the task, the files you'll touch, and the verify command.
- After editing: run the verify command, tick the box here, commit (`type: summary`), then stop and report.
- If a verify command fails twice, stop and explain instead of patching around it.
- Never print secrets. Redaction tests must stay green.

## Week 1: Foundation
- [x] Feedback from 5–10 agent developers
- [x] Public repo + GitHub metadata
- [x] Stack and agent-profile detection
- [x] Dry-run + deterministic Dockerfile generation
- [ ] Golden-file tests (do this next; it gates v0.2.0)
  - [x] Bootstrap the generator on `feat/bootstrap-generator` (approved greenfield scope)
  - [x] One fixture per supported stack/profile (Node/Python × generic/Pi/OpenCode)
  - [x] Cover Dockerfile, Compose, .env.example, the workflow, and .dockerignore
  - [x] Same input gives byte-identical output on repeated runs
  - [x] Fake secrets in fixtures never appear in output
  - [x] Local verification: `python3 -m unittest discover -s tests -v`
  - [x] Docker smoke: `python3 scripts/smoke-containers.py`
  - [ ] Confirm a green GitHub CI run (workflow added; branch not pushed)
  - Done when: `python3 -m unittest discover -s tests -v` passes locally and in CI

## Week 2: MVP
- [x] Compose + .env.example generation
- [x] GitHub Actions cloud-build workflows
- [x] Validation + secret-redaction checks
- [x] Two example apps verified in remote CI
- [x] v0.1.0 published with quick-start guide

## Week 3: SEO and organic launch
- [x] Tutorials: OpenCode Docker, Pi-agent Docker, GitHub Actions + GHCR
- [ ] Demo assets: 30–60s terminal recording (dry-run → generate → green CI) and a before/after image
  - Done when: files are in `docs/` and linked from the README
- [ ] Community lists: shortlist 3–5 relevant awesome-lists, read their contribution rules, open one PR each
  - Done when: PR URLs are logged in `docs/launch-log.md`
- [ ] Share tested demos: re-run the example in a clean environment first
  - One post per channel: what it does, a 2-command try-it, and honest limits
  - Follow each channel's self-promotion rules
  - Done when: post URLs are logged, and every comment gets a reply within 24h

## Week 4: Measure and improve
- [x] Issue reports and first-user feedback collected
- [ ] Unsupported-project errors: each says what was detected, why it's unsupported, what to do next, and links an issue template
  - Done when: golden stderr tests cover at least 3 unsupported cases
- [x] Before/after deployment case study
- [ ] Release v0.2.0: scope is the top 3 recurring issues, the new error messages, and golden tests
  - Done when: changelog written, tag pushed, release workflow green, quick-start works from scratch
- [ ] Adoption review: stars, unique clones/views, GHCR pulls, tutorial views, external issues
  - Set thresholds BEFORE looking at the numbers
  - Done when: `docs/retro.md` records one decision (double down on content / fix onboarding / new sub-niche / pause)
