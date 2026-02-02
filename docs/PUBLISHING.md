# Publishing Guide

This project is ready to publish as an open-source Python package and GitHub repository.

## 1) Prepare metadata

- Update `pyproject.toml`:
  - `project.name` (must be unique on PyPI)
  - `project.urls.*` to your real GitHub repo
  - version number (`project.version`)
- Confirm `README.md` reflects current API and CLI usage.
- Ensure `LICENSE` is present and matches `project.license`.

## 2) Push to GitHub

```bash
git init
git add .
git commit -m "release: publish claw-codex 0.2.0"
git branch -M main
git remote add origin git@github.com:<org-or-user>/<repo>.git
git push -u origin main
```

If a remote already exists, just commit and push your branch.

This repo includes GitHub Actions for:

- CI: `.github/workflows/ci.yml`
- Publishing: `.github/workflows/publish.yml`

## 3) Build distributions

```bash
python -m pip install --upgrade build twine
python -m build
```

Expected artifacts:

- `dist/<name>-<version>.tar.gz`
- `dist/<name>-<version>-py3-none-any.whl`

## 4) Verify package before upload

```bash
twine check dist/*
```

Optional smoke test in a clean virtualenv:

```bash
python -m venv /tmp/claw-smoke
source /tmp/claw-smoke/bin/activate
pip install dist/*.whl
python -c "from claw_codex import ClawCodexClient; print('ok')"
```

## 5) Publish to TestPyPI (recommended)

```bash
twine upload --repository testpypi dist/*
```

Install test build:

```bash
pip install -i https://test.pypi.org/simple/ <your-package-name>
```

Or run the `Publish` workflow manually and select `testpypi`.

## 6) Publish to PyPI

```bash
twine upload dist/*
```

Or create a GitHub Release (triggers publish to PyPI), or run the `Publish` workflow with `pypi`.

## 7) Tag release on GitHub

```bash
git tag v0.1.0
git push origin v0.1.0
```

Create a GitHub Release with changelog notes and the same version.
