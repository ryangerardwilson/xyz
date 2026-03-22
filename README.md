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
- **North Star metrics** capture how well the job contributes to strategy:
  - **Alignment** — does this move the north star forward?
  - **Impact score** — relative magnitude if we nail it.
  - **Embodiment score** — how well it reflects our product principles.

Because every entry is framed that way, xyz doubles as a thinking tool: 
it nudges your backlog toward compounding bets, cross-team clarity, and 
asymmetric growth instead of incremental checklists. Hands stay on the 
keyboard with vim-style navigation, quick editor hops, and a deterministic 
CLI for scripting JTBD plus North Star metric tasks.

---

## Installation

### Prebuilt binary (Linux x86_64)

`xyz` publishes PyInstaller bundles with each GitHub release. The quickest way
to install the latest release is via the helper script:

```bash
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/xyz/main/install.sh | bash
```

Manually add this to `~/.bashrc`, then reload your shell:

```bash
export PATH="$HOME/.xyz/bin:$PATH"
source ~/.bashrc
```

The script downloads the `xyz-linux-x64.tar.gz` artifact, extracts it into
`~/.xyz/app`, and drops a shim in `~/.xyz/bin`.

Installer flags of note:

- `-v <x.y.z>` or `--version <x.y.z>`: install a specific tagged release (`v0.3.0`, etc.).
- `-v` with no argument: print the latest available release version without installing.
- `-u` or `--upgrade`: reinstall only if GitHub has a newer release than your current local version.
- `-b /path/to/xyz` or `--binary /path/to/xyz`: install from a previously extracted local binary.
- `-n` or `--no-modify-path`: compatibility no-op alias; the installer never edits shell config files automatically.

Once installed, the binary itself also supports:

- `xyz -h` to show help
- `xyz -v` to print the installed version
- `xyz -u` to reinstall via the latest installer script if a newer release exists
- `xyz conf` to open the user config in your editor

If you want an offline install, extract the release archive first and then pass
the local `xyz` binary to `install.sh -b`.

### From source

If you’d rather run directly from the repo (handy for development or non-Linux
hosts), install the source dependencies first:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
```

After that, use either the installed command shape (`xyz ...`) or the source
entrypoint (`.venv/bin/python main.py ...`).

---

## Features

- **Agenda + Month views** with Vim-style `hjkl` navigation
- **Buckets** (`personal_development`, `thing`, `economic`) to segment work; press `Tab` in Agenda to cycle filters or show all
- **Single-key view toggle (`a`)** to flip between agenda and month views instantly
- **Editing shortcuts** — `i` for quick single-field tweaks, `I` to edit the full task payload as pretty JSON in `$EDITOR`
- **CLI-first workflow** with `ls`, `a`, `e`, and `d` commands plus stable `edit_id` references
- **North Star metrics** (`p`, `q`, `r`) capturing Jesus' will alignment, outward impact, and embodied practice alongside JTBD fields
- **Quick delete** by double–tapping `d` (`dd`) in Agenda or the month’s task list
- **Month/Year jumping** inside the month view with `Ctrl+h/l` and `Ctrl+j/k`
- **CSV-backed storage** (JTBD + metrics) with a thin `CalendarService`

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

### North Star metrics (p / q / r)

- **p (Jesus' will alignment)** — How aligned was this with Jesus-like values: love, truth, humility, stewardship?
- **q (outward impact)** — What good did it create in the world around you: work, family, service, finances?
- **r (embodied practice)** — Did I honour my body and nervous system while doing it, or did I sacrifice them?

Score each dimension on a 0–10 scale (decimals welcome). The trio keeps the
backlog tethered to mission, nudges you to look beyond personal output, and
surfaces which jobs genuinely advance the Kingdom you’re stewarding.

---

## Requirements

- Python 3.11+
- A Unix-y terminal with `curses`

Once dependencies are installed, these are the canonical command paths:

```bash
xyz -h
xyz -v
xyz conf
xyz tui
xyz ls -all 5
```

---

## Configuration

`xyz` looks for `$XDG_CONFIG_HOME/xyz/config.json` (fallback
`~/.config/xyz/config.json`). Trailing commas are tolerated.

Use `xyz conf` to create or open that file in `$VISUAL`, `$EDITOR`, or `vim`.

Example config:

```json
{
  "data_csv_path": "/home/example/.local/share/xyz/events.csv"
}
```

- `data_csv_path` (optional) overrides where tasks are stored. Defaults to `$XDG_DATA_HOME/xyz/event.csv` (fallback `~/.xyz/event.csv`).

The config loader ensures parent directories exist and will fall back
gracefully if fields are missing.

- Data is stored in CSV rows with columns `bucket`, `x`, `y`, `z`, `p`, `q`, and `r`.

---

## Usage

### Curses UI

Run `xyz tui` and use the shortcuts below. Tasks are loaded from the CSV
path in config. Editing a task writes it as JSON to a temp file, opens
`$EDITOR`, and saves changes back to CSV after validation.

### CLI

List upcoming items by due date (ascending):

```
xyz ls -all 5
xyz ls -per 10
xyz ls -eco 3
```

Create via editor:

```bash
xyz a
```

Create directly (no editor):

```bash
xyz a -x "2026-01-26 00:00" -y "learned to cook pasta" -z "throw a nice party" -p "6" -q "7" -r "5" -bkt per
```

Edit/delete by stable CSV id (`edit_id` in `ls` output):

```bash
xyz e -id 12
xyz e -id 12 -y "updated outcome" -p "8.5" -bkt eco
xyz d -id 12
```

- `e` and `d` are stable by `-id` and do not depend on the visible `ls` serial number.
- `-bkt` supports `per`, `tng`, `eco`.
- `xyz` and `xyz -h` print the same command help.

---

## Keyboard Shortcuts

### Global

- `q` / `Q` – Quit
- `?` – Toggle help overlay
- `t` – Jump to today
- `a` – Toggle between month and agenda views

### Agenda & Month (shared)

- `i` – Edit the focused field (or create when empty) via `$EDITOR`
- `I` – Open the entire selected row as pretty JSON for editing
- `n` – Create a new event
- `h` / `j` / `k` / `l` – Move selection
- `dd` – Delete selected task
- `Tab` – Cycle bucket filter

### Month view

- `Enter` – Toggle focus between calendar grid and day’s task list
- `Ctrl+h` / `Ctrl+l` – Previous / next month
- `Ctrl+j` / `Ctrl+k` – Next / previous year

### Agenda-only extras

- `B` – Edit bucket for selected task via `$EDITOR`
- `,xr` – Toggle expanded/collapsed state for current row

### Overlays & leader

- `Esc` – Dismiss help, cancel leader, or exit month-task focus
- Leader sequences time out after 1 second

---

## Troubleshooting

- **Invalid JSON in config**: Trailing commas are auto-stripped; otherwise the loader falls back to defaults.
- **Editor errors**: If `$EDITOR` exits non-zero or the JSON fails validation, xyz shows an overlay and discards changes.

---

## Architecture Highlights

- `main.py` – thin entrypoint; delegates to `Orchestrator`
- `orchestrator.py` – curses lifecycle, input routing, leader logic, CLI handler
- `calendar_service.py` – loading/upserting/deleting JTBD + metric tasks in CSV storage
- `view_agenda.py` / `view_month.py` – rendering + navigation, including `Ctrl+h/l` month jumps and `dd` deletion states

All modules live in a flat repo structure for now.

---

## Development

- Run TUI: `.venv/bin/python main.py tui`
- CLI help: `.venv/bin/python main.py -h`
- Tests: `.venv/bin/python -m pytest`
- Python 3.11+
- Source checkout dependency: `rgw-cli-contract==0.1.2`
- App logic remains stdlib-first (`curses`, `csv`, `json`, etc.)

Feel free to open issues or PRs with new view ideas (week/day), ICS export
support, or other workflow improvements for xyz.
