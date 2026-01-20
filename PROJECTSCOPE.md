# Project Scope

## 1. Overview

`xyz` is a **Vim-first, terminal-native task tracker** written in Python with `curses`. It focuses on keyboard workflows for inspecting schedules, runs entirely in the terminal, and supports deterministic CLI commands built around x/y/z tasks. Tasks are defined by three fields: trigger `x` (timestamp), outcome `y`, and impact `z` (optional).

---

## 2. Core Design Principles

- **Terminal-native UI** – pure `curses`; no GUI toolkits.
- **Direct view toggling** – single-key `a` flips between agenda and month views; leader remains available for future chords (currently unused).
- **External editing via Vim** – pressing `i` dumps the selected task (x/y/z) to JSON, opens `$EDITOR` (default `vim`), then re-imports the edited JSON.
- **Thin entrypoint** – `main.py` must stay tiny.
- **Central orchestrator** – `orchestrator.py` handles CLI parsing, curses lifecycle, structured CLI handling, and the between-view policy.
- **Flat layout** – small modules at repo root (`calendar_service.py`, etc.).
- **XDG-friendly config** – `$XDG_CONFIG_HOME/xyz/config.json` (fallback `~/.config/xyz/config.json`).
- **Inspectable storage** – tasks stored in a CSV with x/y/z columns (default `$XDG_DATA_HOME/xyz/event.csv`, fallback `~/.xyz/event.csv`).
- **Safe terminal handling** – always restore terminal state on exit.
- **Deterministic x/y/z flow** – CLI, TUI, and storage all share the same three-field contract.

---

## 3. Explicit Non-Goals

- CalDAV/Google/Outlook sync (read-only exports may arrive later).
- Background daemons, reminders, notifications.
- Mouse/touch interaction.
- GUI toolkits (Textual, urwid, Qt, GTK, etc.).
- Multi-user collaboration or sharing.
- Anything that requires background jobs or OAuth (until priorities change).

Natural-language assistants are currently out-of-scope; the CLI focuses on deterministic x/y/z commands.

---

## 4. Application Entry & Control Flow

### `main.py`
- Set terminal defaults (e.g., `ESCDELAY`).
- Instantiate `Orchestrator` and pass CLI args.
- Exit with orchestrator’s return code.

### `orchestrator.py`
- Load config (data path).
- Determine mode: curses UI or structured CLI when flags are provided.
- Manage `CalendarService`, `MonthView`, `AgendaView`, and the leader/overlay state machine.
- Handle `dd` deletion flow and month navigation.

`main.py` must remain slim; orchestration/logging/routing lives in `orchestrator.py`.

---

## 5. Implemented Feature Set (v0)

1. **Views**
   - `a` toggles between Agenda and Month views, preserving Vim-style navigation and jump-to-today logic.

2. **Navigation**
   - `hjkl` to move day/entry selection.
   - `Ctrl+h/l` in month view for previous/next month.
   - `Ctrl+j/k` in month view for next/previous year.
   - `Tab` toggles between month grid and day’s events list.
   - `t` jumps to today globally.

3. **Editing**
   - `i` opens `$EDITOR` with selected event(s) serialized as JSON (single events open as a plain object, multiple as an array). Saves back via `CalendarService.upsert_event`.

4. **Deletion**
   - `dd` deletes the selected event in agenda/month events list. First `d` arms deletion for 600ms; second `d` confirms.

5. **Persistence**
   - `calendar_service.py` loads/saves CSV, handles upserts, deletes (now x/y/z tasks).

6. **Structured CLI**
   - `main.py` parses `-x/-y/-z` flags and delegates to `Orchestrator.handle_structured_cli`.
   - The handler validates input, applies storage updates, and prints the resulting x/y/z JSON.

7. **Help overlay (`?`)**
   - Lists the current shortcuts (global, leader, delete, month jumps, etc.).

---

## 6. Configuration & Storage

### Config (`config.json`)
- Fields: `data_csv_path` (optional). Trailing commas tolerated.
- Default data path: `$XDG_DATA_HOME/xyz/event.csv` (fallback `~/.xyz/event.csv`).
- Example:
  ```json
  {
    "data_csv_path": "/home/example/.local/share/xyz/event.csv"
  }
  ```

### Storage
- CSV columns: `x` (timestamp trigger, YYYY-MM-DD HH:MM:SS), `y` (task outcome), `z` (impact; all three required for new CLI-created tasks).
- `calendar_service.delete_event` removes exact matches; `upsert_event` handles replacements.

### External edit contract
- JSON object with `x/y/z` (legacy `datetime/event/details` still accepted when parsing), validated via `models.normalize_event_payload`.

---

## 7. Interaction & Modes

- **Normal mode**: default navigation state.
- **View toggle**: `a` flips between agenda and month instantly; leader remains for potential future sequences (currently unused).
- **Insert/Edit (external)**: triggered by `i`, leaves curses, opens `$EDITOR`, returns with updated tasks (x/y/z).
- **Delete pending state**: first `d` arms deletion, second `d` confirms.

---

## 8. Keybinding Reference (current)

| Key / Sequence | Scope | Action |
| -------------- | ----- | ------ |
| `q` / `Q`      | global | Quit |
| `?`            | global | Toggle help |
| `t`            | global | Jump to today |
| `a`            | global | Toggle Month / Agenda views |
| `i`            | view (item) | Edit/create via `$EDITOR` |
| `n`            | agenda + month events | Create a new event |
| `dd`           | agenda + month events | Delete selected event |
| `Ctrl+h` / `Ctrl+l` | month view | Previous / next month |
| `Ctrl+j` / `Ctrl+k` | month view | Next / previous year |
| `h/j/k/l`      | agenda + month | Move selection |
| `Tab`          | month view | Toggle grid vs events focus |
| `Esc`          | overlays / leader | Dismiss overlays, cancel leader, exit month events focus |

Leader sequences may expand (week/day views) post-v0.

---

## 9. Success Criteria

- UI remains responsive (<16ms redraw) in both views.
- Editing loop (navigate → `i` → edit JSON → save) works end-to-end.
- Structured CLI validates x/y/z fields and surfaces clear errors when input is invalid.
- Config defaults resolve automatically; trailing commas don’t break parsing.
- Documentation (README + ProjectScope) matches actual behavior.

---

## 10. Roadmap

### Short-term
- Add tests for `calendar_service` and structured CLI flows.
- Improve month view layout (weekday headers, spacing, dynamic event panes). ✔️

### Medium-term
- Add week/day views (` ,w `/` ,d `) reusing Agenda/Month patterns.
- Provide ICS export/import utilities.
- Expand CLI ergonomics (bulk operations, templates, etc.) for xyz.
- Expose configurable keybindings via config.

### Deferred
- Sync providers (CalDAV/Google/Outlook).
- GUI front-ends.
- Notifications/reminders.
- Multi-user shared calendars.

Scope creep rule: any feature needing background jobs, OAuth, or remote services stays out until explicitly prioritized.
