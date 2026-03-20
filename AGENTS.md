# Repository Guidelines

## Workspace Defaults
- Follow `/home/ryan/Documents/agent_context/CLI_TUI_STYLE_GUIDE.md` for CLI/TUI taste and help shape.
- Follow `/home/ryan/Documents/agent_context/CANONICAL_REFERENCE_IMPLEMENTATION_FOR_CLI_AND_TUI_APPS.md` for executable contract details such as `-h`, `-v`, `-u`, installer behavior, release workflow expectations, and regression expectations.
- This file only records `xyz`-specific constraints or durable deviations.

## Project Structure & Module Organization
This repository is a flat Python project centered on a terminal UI task tracker.
- Core runtime: `main.py` (entrypoint), `orchestrator.py` (app flow/input routing), `view_agenda.py`, `view_month.py`, `ui_base.py`.
- Domain/data: `models.py`, `calendar_service.py`, `store.py`, `state.py`, `structured_command.py`.
- Config and paths: `config.py`, `paths.py`, `keys.py`, `_version.py`.
- Packaging/release: `install.sh`, `.github/workflows/release.yml`, `.github/scripts/find-python-url.py`.
- Assets/docs: `template.csv`, `README.md`, `PROJECTSCOPE.md`.

## Build, Test, and Development Commands
- `python main.py`: launch the curses UI locally.
- `python main.py -h`: show CLI help.
- `python main.py -b personal_development -x "2026-01-26 00:00" -y "..." -z "..." -p 7 -q 8 -r 6`: add an entry non-interactively.
- `python main.py -v`: print version.
- `python main.py -u`: trigger upgrade flow via installer script.
- `python -m pytest`: run the committed contract regression tests.
- `bash install.sh -v`: inspect installer/release version behavior.

## Coding Style & Naming Conventions
- Target Python 3.11+; use 4-space indentation and PEP 8 defaults.
- Prefer type hints (`str | None`, `list[str]`) and small, single-purpose functions.
- Use `snake_case` for functions/variables/modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep modules stdlib-first; the only required source-checkout dependency is `rgw-cli-contract`.

## Testing Guidelines
This repo ships committed `pytest` contract tests at the project root.
- Keep contract regressions in `test_*.py` files so `./push_release_upgrade.sh` picks them up.
- Prioritize coverage for CLI argument parsing, config editing, version/upgrade plumbing, CSV persistence, validation, and state transitions.
- For UI-heavy changes, include manual verification steps in PRs (key paths exercised, expected behavior).

## Commit & Pull Request Guidelines
Git history currently uses short lowercase commit subjects (mostly `sync`). For new contributions:
- Use concise imperative subjects with context (example: `fix agenda cursor wrap on empty day`).
- Keep commits focused; separate refactors from behavior changes.
- PRs should include: purpose, behavior summary, manual test steps/commands, and screenshots or terminal captures for visible TUI changes.
- Link related issues when applicable.

## Security & Configuration Tips
- Do not commit personal data files or local config.
- Store runtime settings in `$XDG_CONFIG_HOME/xyz/config.json` (or `~/.config/xyz/config.json`).
- Use `data_csv_path` to point to local task data outside the repository.
