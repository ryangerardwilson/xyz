# tcal

`tcal` is a vim-first, terminal-native task tracker for people who keep their hands on the keyboard. It offers fast month/agenda navigation, external editing via your terminal editor, and a natural-language CLI powered by OpenAI’s structured outputs.

---

## Installation

### Prebuilt binary (Linux x86_64)

`tcal` publishes PyInstaller bundles with each GitHub release. The quickest way to install the latest release is via the helper script:

```bash
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/tcal/main/install.sh | bash
```

The script downloads the `tcal-linux-x64.tar.gz` artifact, extracts it into `~/.tcal/app`, and drops a shim in `~/.tcal/bin`. It will attempt to add that directory to your `PATH` (unless you opt out) so you can just run `tcal` from any shell.

Installer flags of note:

- `--version <x.y.z>` or `-v <x.y.z>`: install a specific tagged release (`v0.3.0`, etc.).
- `--version` (no argument): print the latest available release version without installing.
- `--upgrade`: reinstall only if GitHub has a newer release than your current local version.
- `--binary /path/to/tcal-linux-x64.tar.gz`: install from a previously downloaded archive.
- `--no-modify-path`: skip auto-updating shell config files; the script will print the PATH export you should add manually.

Once installed, the binary itself also supports:

- `tcal --version` (or `-V`) to print the installed version
- `tcal --upgrade` to reinstall via the latest installer script if a newer release exists

You can also download the archive directly from the releases page and run `install.sh --binary` if you prefer.

### From source

If you’d rather run directly from the repo (handy for development or non-Linux hosts), follow the requirements below and execute `python main.py` like before.

---

## Features

- **Agenda + Month views** with Vim-style `hjkl` navigation
- **Single-key view toggle (`a`)** to flip between agenda and month views instantly
- **External editing** (`i`) that opens the selected task as JSON in `$EDITOR` (default `vim`)
- **Natural-language CLI** (e.g. `python main.py "finish studying calculus by March 1"`) with intents for creating, listing, and rescheduling tasks (absolute or relative time shifts)
- **Quick delete** by double–tapping `d` (`dd`) in Agenda or the month’s task list
- **Month/Year jumping** inside the month view with `Ctrl+h/l` and `Ctrl+j/k`
- **CSV-backed storage** with a thin `CalendarService`

---

## Requirements

- Python 3.11+
- A Unix-y terminal with `curses`
- OpenAI API key (only required for the natural-language CLI path)

Install dependencies (none besides stdlib) and run from the repo root:

```bash
python main.py        # launches curses UI
python main.py "show me today's events"   # natural-language CLI
```

---

## Configuration

`tcal` looks for `$XDG_CONFIG_HOME/tcal/config.json` (fallback `~/.config/tcal/config.json`). Trailing commas are tolerated.

Example config:

```json
{
  "data_csv_path": "/home/example/.local/share/tcal/events.csv",
  "openai_api_key": "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "model": "gpt-4o-mini"
}
```

- `data_csv_path` (optional) overrides where tasks are stored. Defaults to `$XDG_DATA_HOME/tcal/event.csv` (fallback `~/.tcal/event.csv`).
- `openai_api_key` unlocks natural-language intents. If omitted, the CLI UI still works.
- `model` lets you pin a specific OpenAI chat model; defaults to `gpt-4o-mini`.

The config loader ensures parent directories exist and will fall back gracefully if fields are missing.

---

## Usage

### Curses UI

Run `python main.py` and use the shortcuts below. Tasks are loaded from the CSV path in config. Editing a task writes it as JSON to a temp file, opens `$EDITOR`, and saves changes back to CSV after validation.

### Natural-language CLI

If `openai_api_key` is set, any quoted argument is interpreted as a natural-language command:

```
python main.py "finish studying calculus by March 1 2026"
python main.py "list tasks this month about infra"
python main.py "reschedule calculus study to March 5"
python main.py "show all tasks next week"
```

Supported intents (still named `create_event`/`list_events`/`reschedule_event` in code for now) map to the task fields `x` (timestamp trigger), `y` (outcome), and `z` (impact):

- `create_event`: add a new task with x/y/z (all required for the CLI path; missing any component triggers a rejection with suggested rephrasing)
- `list_events`: show tasks for `today`, `tomorrow`, `this_week`, `next_month`, `all`, etc., optionally filtered by keywords (matching y or z)
- `reschedule_event`: move a task to a new absolute x or shift its x by a relative amount (`relative_amount` + `relative_unit` like days/hours/weeks)


The executor validates OpenAI responses against JSON Schema and surfaces errors when the API rejects parameters (e.g., unsupported `max_tokens`).

---

## Keyboard Shortcuts

| Key / Sequence | Scope | Action |
| -------------- | ----- | ------ |
| `q` / `Q`      | global | Quit |
| `?`            | global | Toggle help overlay |
| `t`            | global | Jump to today |
| `a`            | global | Toggle between Month / Agenda views |
| `i`            | view (item) | Edit/create via `$EDITOR` (x/y/z) |
| `dd`           | agenda + month tasks | Delete selected task |
| `Ctrl+h` / `Ctrl+l` | month view | Previous / next month |
| `Ctrl+j` / `Ctrl+k` | month view | Next / previous year |
| `h/j/k/l`      | agenda + month | Move selection | 
| `Tab`          | month view | Toggle focus between calendar grid and day’s task list |
| `Esc`          | overlays / leader | Dismiss help / cancel leader / exit month-task focus |

Leader sequences time out after 1 second.

---

## Troubleshooting

- **Missing OpenAI key**: CLI prints “Missing openai_api_key…” and exits with code 1. Set the key in config.
- **HTTP 400 / API errors**: The natural-language executor reports the exact message returned by OpenAI (e.g., unsupported parameter). Adjust config/model accordingly.
- **Invalid JSON in config**: Trailing commas are auto-stripped; otherwise the loader falls back to defaults.
- **Editor errors**: If `$EDITOR` exits non-zero or the JSON fails validation, tcal shows an overlay and discards changes.

---

## Architecture Highlights

- `main.py` – thin entrypoint; delegates to `Orchestrator`
- `orchestrator.py` – curses lifecycle, input routing, leader logic, NL CLI entry
- `calendar_service.py` – loading/upserting/deleting tasks (x/y/z) in CSV storage
- `actions.py` / `intents.py` / `nl_executor.py` – structured OpenAI intents (create/list/reschedule)
- `date_ranges.py` – helpers for “today”, “this_week”, “next_month”, etc.
- `view_agenda.py` / `view_month.py` – rendering + navigation, including `Ctrl+h/l` month jumps and `dd` deletion states

All modules live in a flat repo structure for now.

---

## Development

- Run: `python main.py`
- Tests: invoke your preferred runner / add `pytest` as needed (none included yet)
- Python 3.11+
- Pure stdlib dependencies (`curses`, `csv`, `json`, etc.)

Feel free to open issues or PRs with new view ideas (week/day), ICS export support, or improved NL tooling.
