# Contributing to Wijjit

Thanks for your interest in improving Wijjit! This guide covers the basics of
getting set up and the conventions the project follows.

## Development setup

Wijjit uses [`uv`](https://docs.astral.sh/uv/) for environment and package
management.

```bash
git clone https://github.com/thomas-villani/wijjit.git
cd wijjit
uv sync --all-extras   # creates .venv with runtime + dev + images extras
```

## Running the checks

All of these run in CI and must pass before a change is merged:

```bash
# Tests (skip the slower benchmark suite for a faster loop)
uv run pytest tests/ --ignore=tests/benchmarks -q

# Formatting, lint, and types
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/            # strict
```

## Testing UI changes headlessly

Wijjit ships a headless harness (`wijjit.testing.WijjitHarness`) that drives a
real app without a TTY, so visual and interaction bugs can be reproduced and
regression-tested. There is also a CLI for printing a demo's screen:

```bash
uv run python -m wijjit.testing examples/basic/hello_world.py --size 80x24
```

Please add a regression test for any bug fix where the harness can reproduce it.
Some real-terminal / OS-specific behaviors can't be driven headlessly; note that
in the PR if so.

## Pull requests

- Branch off `main`; keep PRs focused.
- Match the surrounding code style; modules/classes/functions use NumPy-style
  docstrings.
- Update `CHANGELOG.md` (under `[Unreleased]`) for user-facing changes.
- Make sure the full check suite above is green.

## Project guidance

`CLAUDE.md` documents the architecture and conventions in depth and is a good
orientation for where things live. Outstanding work is tracked in
`RELEASE_PLAN.md` and `issues.md`.

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
