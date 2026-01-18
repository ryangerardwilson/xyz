# Project Scope

## 1. Overview

Tcal is a **Vim-first, terminal-native calendar** written in Python with `curses`. It focuses on fast keyboard workflows for inspecting schedules while keeping storage explicit and inspectable. Users stay in the terminal, navigate with Vim muscle memory, and jump between high-level views with a comma leader.

---

## 2. Core Design Principles

- **Terminal-native UI** – pure `curses`, zero GUI toolkits.
- **Leader-driven ergonomics** – comma (`,`) is the leader; view switches live behind sequences like `,m` (month) and `,a` (agenda).
- **External editing via Vim** – pressing `i` on an item writes its data to a temp JSON file, opens `$EDITOR` (default `vim`), and applies changes on save.
- **Thin entrypoint** – `main.py` just boots the orchestrator.
- **Centralized orchestration** – `orchestrator.py` owns argument parsing, curses lifecycle, and mode routing.
- **Flat layout** – small, single-purpose modules in the repo root until growth justifies folders.
- **XDG-compliant config** – settings live in `$XDG_CONFIG_HOME/tcal/config.json` (fallback `~/.config/tcal/config.json`).
- **Inspectable storage** – event data persists as a Parquet file with a stable schema (via PyArrow) at a user-configurable path.
- **Fail-safe terminal handling** – always restore terminal state, never leave users in broken tty mode.

---

## 3. Explicit Non-Goals

- CalDAV / Google / Outlook sync (read-only exports may come later but are not core).
- Background daemons, push notifications, or reminders.
- Natural-language scheduling assistants or AI integrations.
- Mouse/touch interaction layers.
- GUI toolkits (Textual, urwid, Qt, GTK, etc.).
- Complex plugin systems or embedded scripting engines.
- Multi-user collaboration or shared calendars.

Anything that requires background services, OAuth, or long-running network connections is outside MVP scope.

---

## 4. Application Entry & Control Flow

### `main.py`
- Set minimal terminal env defaults (e.g., `ESCDELAY`).
- Instantiate `Orchestrator` with CLI args/streams.
- Exit with whatever code the orchestrator returns.

### `orchestrator.py`
- Parse CLI arguments (`--version`, `--help`, future flags like `--config`).
- Load config (resolving Parquet path, editor preference, etc.).
- Initialize curses, screen layout, and mode state.
- Route user input to the appropriate view/pane.
- Handle clean shutdown, data persistence, and error messaging.

`main.py` must stay tiny; all policy decisions belong in the orchestrator.

---

## 5. MVP Feature Set (v0 Focus)

1. **Views (Leader accessible)**
   - `,a` Agenda view (chronological list). **Implemented in v0.**
   - `,m` Month view (calendar grid + per-day items). **Implemented in v0.**
   - `,w` Week view (reserved, post-v0).
   - `,d` Day view (reserved, post-v0).

2. **Navigation**
   - Agenda + Month use `h/j/k/l` for horizontal/vertical movement.
   - `t` jumps to today regardless of view.

3. **Editing**
   - Press `i` on the selected agenda entry (or selected day item) to edit in Vim.
   - Tcal serializes the item to JSON with keys `datetime`, `event`, `details`, launches `$EDITOR`, and applies changes if the JSON parses and validates.

4. **Persistence**
   - Data lives in a Parquet file stored at the path specified in config (`data_parquet_path`).
   - A storage module (PyArrow-backed) handles load/save, schema validation, and migration warnings.

5. **Help Overlay**
   - `?` displays keybindings, leader commands, and editing tips.

---

## 6. Configuration & Storage

### 6.1 Config File
- Location: `$XDG_CONFIG_HOME/tcal/config.json` (fallback `~/.config/tcal/config.json`).
- Example:
```json
{
  "data_parquet_path": "/home/ryan/.local/share/tcal/events.parquet",
  "editor": "vim"
}
```
- `data_parquet_path` is required; if missing, default to `~/.local/share/tcal/events.parquet` and ensure directories exist.
- `editor` is optional; fallback order: config → `$EDITOR` env → `vim`.

### 6.2 Parquet Schema (PyArrow)
Columns:
- `datetime` (timestamp[ns]): ISO-formatted local datetime (`YYYY-MM-DD HH:MM:SS`).
- `event` (string): primary description.
- `details` (string): free-form notes (can be empty).

Constraints:
- `datetime` is mandatory and unique per row (enforced in storage layer).
- `event` cannot be empty.
- `details` defaults to `""` if omitted.

### 6.3 External Edit Contract
- On `i`, Tcal writes the selected row to a temp JSON file:
  ```json
  {
    "datetime": "2026-01-18 09:00:00",
    "event": "Standup",
    "details": "Daily sync"
  }
  ```
- Vim (or chosen editor) opens in the user’s terminal.
- When the editor exits with code 0, Tcal re-loads the JSON, validates fields, and writes back to Parquet via PyArrow.
- Invalid JSON or schema violations trigger an overlay warning and discard changes.

---

## 7. Interaction & Modes

- **Normal mode**: default state for navigation and leader commands.
- **Leader sequences**: pressing `,` enters leader mode; the next key selects a view (`m`, `a`, `w`, `d`). Leader waits for one key and times out after ~1 second (configurable later).
- **Insert/Edit mode**: triggered indirectly through external editor (`i`). Tcal exits curses mode, launches Vim, then restores the UI when editing completes.
- **Command palette (future)**: `:` reserved for future commands (`:export`, `:goto 2026-01-01`, etc.).

Mode transitions mirror Vim expectations: `Esc` clears leader state and overlays, `i` launches editor for the focused item, `:` (future) enters command entry.

---

## 8. Keybinding Baseline

| Key / Sequence | Scope | Action |
| --- | --- | --- |
| `q` | global | Quit (prompt if unsaved changes). |
| `?` | global | Toggle help overlay. |
| `t` | global | Jump focus to today. |
| `,m` | global | Switch to Month view. |
| `,a` | global | Switch to Agenda view. |
| `,w` | global | Switch to Week view (placeholder). |
| `,d` | global | Switch to Day view (placeholder). |
| `h` / `l` | month & agenda | Move selection left/right (prev/next day or prev/next entry). |
| `j` / `k` | month & agenda | Move selection down/up (next/prev week in month, next/prev entry in agenda). |
| `i` | item-focused | Edit selected entry in external Vim session. |
| `Esc` | overlays/leader | Dismiss help overlay or cancel leader sequence. |

Keybindings will become configurable via `config.json`, but defaults must feel great out of the box.

---

## 9. Success Criteria

- Launches instantly (<250ms) and exits cleanly without leaving the terminal raw.
- Month + Agenda navigation stay responsive (<16ms redraw budget).
- Parquet file remains valid and deduplicated even after abrupt exits.
- Editing loop (navigate → `i` → edit in Vim → save) works end-to-end without manual file tweaks.
- Config defaults (data path, editor) resolve automatically if unset, and users can override via config file.
- Documentation (README + ProjectScope) remains accurate as views evolve.

---

## 10. Roadmap

### Short-term (v0)
- Implement config loader with XDG resolution and default Parquet path.
- Build PyArrow-backed storage module for `datetime/event/details` schema.
- Render Agenda view list with `hjkl` navigation and selection state.
- Render Month view grid with day selection + peek into day’s events.
- Implement Vim editing loop for selected agenda/month items (`i`).
- Add help/leader overlay describing keybindings.

### Medium-term
- Flesh out Week (` ,w`) and Day (` ,d`) views using the same navigation primitives.
- Expose command palette (`:`) for jump/export operations.
- Add filtering (e.g., tag search) and configurable leader sequences via `config.json`.
- Provide optional ICS export/import utilities.

### Explicitly Deferred
- Network sync providers (CalDAV, Google, Outlook).
- Mobile/GUI front-ends.
- Notifications and reminders.
- Multi-user sharing or invites.

Scope creep checklist: if a feature needs background jobs, OAuth, or third-party APIs, it stays out until priorities change.
