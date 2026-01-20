# Project Scope

## 1. Overview

`tcal` is a **Vim-first, terminal-native task tracker** written in Python with `curses`. It focuses on keyboard workflows for inspecting schedules, runs entirely in the terminal, and now includes an optional natural-language CLI powered by OpenAI structured outputs. Tasks are defined by three fields: trigger `x` (timestamp), outcome `y`, and impact `z` (optional).

---

## 2. Core Design Principles

- **Terminal-native UI** – pure `curses`; no GUI toolkits.
- **Direct view toggling** – single-key `a` flips between agenda and month views; leader remains available for future chords.
- **External editing via Vim** – pressing `i` dumps the selected task (x/y/z) to JSON, opens `$EDITOR` (default `vim`), then re-imports the edited JSON.
- **Thin entrypoint** – `main.py` must stay tiny.
- **Central orchestrator** – `orchestrator.py` handles CLI parsing, curses lifecycle, NL CLI entry, and the between-view policy.
- **Flat layout** – small modules at repo root (`calendar_service.py`, `nl_executor.py`, `actions.py`, etc.).
- **XDG-friendly config** – `$XDG_CONFIG_HOME/tcal/config.json` (fallback `~/.config/tcal/config.json`).
- **Inspectable storage** – tasks stored in a CSV with x/y/z columns (default `$XDG_DATA_HOME/tcal/event.csv`, fallback `~/.tcal/event.csv`).
- **Safe terminal handling** – always restore terminal state on exit.
- **Structured natural-language intents** – OpenAI client uses JSON schema + tool-ready architecture for create/list/reschedule commands.

---

## 3. Explicit Non-Goals

- CalDAV/Google/Outlook sync (read-only exports may arrive later).
- Background daemons, reminders, notifications.
- Mouse/touch interaction.
- GUI toolkits (Textual, urwid, Qt, GTK, etc.).
- Multi-user collaboration or sharing.
- Anything that requires background jobs or OAuth (until priorities change).

Natural-language assistants **are now in-scope** when using structured outputs/tool calling; free-form conversational agents remain out-of-scope for v0.

---

## 4. Application Entry & Control Flow

### `main.py`
- Set terminal defaults (e.g., `ESCDELAY`).
- Instantiate `Orchestrator` and pass CLI args.
- Exit with orchestrator’s return code.

### `orchestrator.py`
- Load config (data path, OpenAI key/model).
- Determine mode: curses UI or natural-language CLI when args are provided.
- Manage `CalendarService`, `MonthView`, `AgendaView`, and the leader/overlay state machine.
- Handle `dd` deletion flow, `Ctrl+h/l` month shifts, and NL executor errors.

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

6. **Natural-language CLI**
   - `nl_executor.py` + `openai_client.py` parse create/list/reschedule intents using JSON schema.
   - `actions.py` executes intents (create event, filter lists by date range/keyword, reschedule via absolute or relative adjustments).

7. **Help overlay (`?`)**
   - Lists the current shortcuts (global, leader, delete, month jumps, etc.).

---

## 6. Configuration & Storage

### Config (`config.json`)
- Fields: `data_csv_path`, `openai_api_key`, `model` (optional). Trailing commas tolerated.
- Default data path: `$XDG_DATA_HOME/tcal/event.csv` (fallback `~/.tcal/event.csv`).
- Example:
  ```json
  {
    "data_csv_path": "/home/example/.local/share/tcal/event.csv",
    "openai_api_key": "sk-proj-...",
    "model": "gpt-4o-mini"
  }
  ```

### Storage
- CSV columns: `x` (timestamp trigger, YYYY-MM-DD HH:MM:SS), `y` (task outcome), `z` (impact, optional for now).
- `calendar_service.delete_event` removes exact matches; `upsert_event` handles replacements.

### External edit contract
- JSON object with `x/y/z` (legacy `datetime/event/details` still accepted when parsing), validated via `models.normalize_event_payload`.

---

## 7. Interaction & Modes

- **Normal mode**: default navigation state.
- **View toggle**: `a` flips between agenda and month instantly; leader remains for future sequences (e.g., `,n` for new).
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
- Natural-language CLI handles create/list/reschedule intents reliably, with clear errors when OpenAI rejects a request.
- Config defaults resolve automatically; trailing commas don’t break parsing.
- Documentation (README + ProjectScope) matches actual behavior.

---

## 10. Roadmap

### Short-term
- Polish natural-language intents (additional ranges, better disambiguation).
- Add tests for `calendar_service`, `actions`, and `nl_executor`.
- Improve month view layout (weekday headers, spacing, dynamic event panes). ✔️

### Medium-term
- Add week/day views (` ,w `/` ,d `) reusing Agenda/Month patterns.
- Provide ICS export/import utilities.
- Expand NL executor with tool-calling (list/search/reschedule dialogs).
- Expose configurable keybindings via config.

### Deferred
- Sync providers (CalDAV/Google/Outlook).
- GUI front-ends.
- Notifications/reminders.
- Multi-user shared calendars.

Scope creep rule: any feature needing background jobs, OAuth, or remote services stays out until explicitly prioritized.
