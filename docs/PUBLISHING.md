# Publishing Guide

This repository uses GitHub Actions + trusted publishing for releases.

## First-time setup (one-time)

1. Create accounts on TestPyPI and PyPI.
2. In each registry, add a **Trusted Publisher** for:
   - Owner: `JayFarei`
   - Repository: `claw-codex`
   - Workflow: `.github/workflows/publish.yml`
3. In GitHub, ensure Actions are enabled for this repository.

## Release workflow (recommended)

1. Bump package version in `pyproject.toml`.
2. Run checks locally:
   ```bash
   python -m pip install --upgrade build twine
   python -m pytest -q
   python -m build
   python -m twine check dist/*
   ```
3. Commit, tag, and push:
   ```bash
   git add .
   git commit -m "release: claw-codex vX.Y.Z"
   git tag -a vX.Y.Z -m "claw-codex vX.Y.Z"
   git push origin main --tags
   ```
4. Create a GitHub Release for `vX.Y.Z`.
5. Confirm success in Actions:
   - Workflow: `Publish`
   - Job: `Publish package`

## Manual publish runs

- TestPyPI: run workflow `Publish` with input `repository=testpypi`.
- PyPI: run workflow `Publish` with input `repository=pypi`.

## Verify install

From PyPI:

```bash
python -m venv /tmp/claw-verify
source /tmp/claw-verify/bin/activate
pip install claw-codex==X.Y.Z
python -c "from claw_codex import ClawCodexClient; print('ok')"
```

From TestPyPI (safer command):

```bash
python -m venv /tmp/claw-test
source /tmp/claw-test/bin/activate
pip install --index-url https://test.pypi.org/simple/ --no-deps claw-codex==X.Y.Z
pip install --index-url https://pypi.org/simple/ 'fastapi>=0.110.0' 'httpx>=0.27.0' 'pydantic>=2.6.0' 'uvicorn>=0.27.0'
python -c "from claw_codex import ClawCodexClient; print('ok')"
```
