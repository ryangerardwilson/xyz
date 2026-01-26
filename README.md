# xyz

`xyz` is a vim-first, terminal-native task tracker built on a sharper 
Jobs-to-Be-Done habit. It helps you write outcome statements that steer 
product, comms, and ops toward non-linear growth instead of busywork 
progress tracking.

Here’s the practical upgrade it enforces:

> **When X happens, I want Y outcome so I can Z.**

- **X = target trigger** — the point in time you’ll check whether the outcome is real.
- **Y = desired progress/outcome** — the change you need, not the tool you will use.
- **Z = why it matters (value/impact)** — the reason this progress is worth pursuing.

Because every entry is framed that way, xyz doubles as a thinking tool: 
it nudges your backlog toward compounding bets, cross-team clarity, and 
asymmetric growth instead of incremental checklists. Hands stay on the 
keyboard with vim-style navigation, quick editor hops, and a deterministic 
CLI for scripting x/y/z tasks.

---

## Installation

### Prebuilt binary (Linux x86_64)

`xyz` publishes PyInstaller bundles with each GitHub release. The quickest way
to install the latest release is via the helper script:

```bash
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/xyz/main/install.sh | bash
```

The script downloads the `xyz-linux-x64.tar.gz` artifact, extracts it into
`~/.xyz/app`, and drops a shim in `~/.xyz/bin`. It will attempt to add that
directory to your `PATH` (unless you opt out) so you can just run `xyz` from
any shell.

Installer flags of note:

- `--version <x.y.z>` or `-v <x.y.z>`: install a specific tagged release (`v0.3.0`, etc.).
- `--version` (no argument): print the latest available release version without installing.
- `--upgrade`: reinstall only if GitHub has a newer release than your current local version.
- `--binary /path/to/xyz-linux-x64.tar.gz`: install from a previously downloaded archive.
- `--no-modify-path`: skip auto-updating shell config files; the script will print the PATH export you should add manually.

Once installed, the binary itself also supports:

- `xyz -v` to print the installed version
- `xyz -u` to reinstall via the latest installer script if a newer release exists

You can also download the archive directly from the releases page and run
`install.sh --binary` if you prefer.

### From source

If you’d rather run directly from the repo (handy for development or non-Linux
hosts), follow the requirements below and execute `python main.py` like before.

---

## Features

- **Agenda + Month views** with Vim-style `hjkl` navigation
- **Buckets** (`personal_development`, `thing`, `economic`) to segment work; press `Tab` in Agenda to cycle filters or show all
- **Single-key view toggle (`a`)** to flip between agenda and month views instantly
- **External editing** (`i`) that opens the selected task as JSON in `$EDITOR`
- **Structured CLI** with explicit `-x/-y/-z` flags for scripting tasks deterministically
- **Quick delete** by double–tapping `d` (`dd`) in Agenda or the month’s task list
- **Month/Year jumping** inside the month view with `Ctrl+h/l` and `Ctrl+j/k`
- **CSV-backed storage** with a thin `CalendarService`

---

## Outcome-first JTBD philosophy

xyz treats every entry as a refined Jobs-to-Be-Done statement: *"When X
happens, I want Y outcome so I can Z."* That framing, rooted in Clayton
Christensen’s JTBD theory, keeps planning focused on the progress users hire
tools to make—not on the mechanics of any specific feature. Each field in the
app maps directly to that structure:

- **X (target trigger)** fixes the job to when you’ll verify reality, keeping progress time-bound and concrete.
- **Y (desired progress/outcome)** expresses the advancement the user needs, free from solution verbs like “send” or “track.”
- **Z (why it matters/value/impact)** surfaces the deeper motivation (reduce stress, earn trust, hit a KPI), guiding prioritization toward high-leverage bets.

### Goal-horizon guidance

- If **X** is roughly a **3-month goal**, make sure **Y/Z** read as *realistic and grounded*.
- If **X** points to a **5-year goal**, keep **Y/Z** *expansive yet meaningful*.
- If **X** gestures at a **lifetime goal**, let **Y/Z** feel *deeply values-driven*.

By enforcing this outcome-first language, xyz behaves more like a non-linear
to-do system: you start with the value you need to create, then explore
multiple ways to realize it. That mindset unlocks non-obvious solutions, aligns
cross-functional teams on user value, and steers roadmap decisions toward
compounding results instead of incremental busywork.

---

## Requirements

- Python 3.11+
- A Unix-y terminal with `curses`

Install dependencies (none besides stdlib) and run from the repo root:

```bash
python main.py                       # launches curses UI (TUI)
python main.py -x "2026-01-26 00:00" -y "learned to cook pasta" -z "throw a nice party"
```

---

## Configuration

`xyz` looks for `$XDG_CONFIG_HOME/xyz/config.json` (fallback
`~/.config/xyz/config.json`). Trailing commas are tolerated.

Example config:

```json
{
  "data_csv_path": "/home/example/.local/share/xyz/events.csv"
}
```

- `data_csv_path` (optional) overrides where tasks are stored. Defaults to `$XDG_DATA_HOME/xyz/event.csv` (fallback `~/.xyz/event.csv`).

The config loader ensures parent directories exist and will fall back
gracefully if fields are missing.

---

## Usage

### Curses UI

Run `python main.py` and use the shortcuts below. Tasks are loaded from the CSV
path in config. Editing a task writes it as JSON to a temp file, opens
`$EDITOR`, and saves changes back to CSV after validation.

### Structured CLI

Use the deterministic flags whenever you want to script or quickly log a task:

```
python main.py -b personal_development -x "2026-01-26 00:00" -y "learned to cook pasta" -z "throw a nice party"
python main.py -b economic -x "2026-02-01 09:00" -y "ship launch blog" -z "prep launch recap"
```

- `-b` (required): bucket (`personal_development`, `thing`, or `economic`).
- `-x` (required): trigger timestamp (`YYYY-MM-DD HH:MM[:SS]`). Seconds are optional.
- `-y` (required): outcome text.
- `-z` (required): impact text.

Successful commands print the stored JSON payload. Validation/storage failures
return exit code `1` with a descriptive error.

---

## Keyboard Shortcuts

| Key / Sequence | Scope | Action | | -------------- | ----- | ------ | | `q` /
`Q`      | global | Quit | | `?`            | global | Toggle help overlay | |
`t`            | global | Jump to today | | `a`            | global | Toggle
between Month / Agenda views | | `i`            | agenda + month | Edit/create
via `$EDITOR` (x/y/z) | | `n`            | agenda + month tasks | Create a new
event | | `dd`           | agenda + month tasks | Delete selected task | |
`Ctrl+h` / `Ctrl+l` | month view | Previous / next month | | `Ctrl+j` /
`Ctrl+k` | month view | Next / previous year | | `h/j/k/l`      | agenda +
month | Move selection | | `Tab`          | agenda / month | Cycle bucket
filter | | `Enter`        | month view | Toggle focus between calendar grid and
day’s task list | | `B`            | agenda | Edit bucket for selected task via
`$EDITOR` | | `,xr`          | agenda | Toggle expanded/collapsed state for
current row | | `Esc`          | overlays / leader | Dismiss help / cancel
leader / exit month-task focus |

Leader sequences time out after 1 second.

---

## Troubleshooting

- **Invalid JSON in config**: Trailing commas are auto-stripped; otherwise the loader falls back to defaults.
- **Editor errors**: If `$EDITOR` exits non-zero or the JSON fails validation, xyz shows an overlay and discards changes.

---

## Architecture Highlights

- `main.py` – thin entrypoint; delegates to `Orchestrator`
- `orchestrator.py` – curses lifecycle, input routing, leader logic, CLI handler
- `calendar_service.py` – loading/upserting/deleting tasks (x/y/z) in CSV storage
- `view_agenda.py` / `view_month.py` – rendering + navigation, including `Ctrl+h/l` month jumps and `dd` deletion states

All modules live in a flat repo structure for now.

---

## Development

- Run: `python main.py`
- Tests: invoke your preferred runner / add `pytest` as needed (none included yet)
- Python 3.11+
- Pure stdlib dependencies (`curses`, `csv`, `json`, etc.)

Feel free to open issues or PRs with new view ideas (week/day), ICS export
support, or other workflow improvements for xyz.
