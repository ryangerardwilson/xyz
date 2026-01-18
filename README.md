# tcal

Tcal is a **Vim-first, terminal-native calendar** for folks who live in Vim and want a fast way to browse days, weeks, and months without leaving the terminal. It is written in Python using `curses`, keeps a flat project layout, and mirrors the thin-`main.py`/central-`orchestrator.py` pattern used across my other tools.

---

## Status

🚧 Early scaffolding. The current build now targets the v0 contract: Agenda + Month views, external editing via `$EDITOR` on a temp JSON, and Parquet-backed storage.

---

## Philosophy

- **Keyboard supreme** – every action is reachable with predictable, Vim-inspired bindings.
- **Terminal-native** – no GUI toolkits, no mouse assumptions, no background daemons.
- **Transparent storage** – events live in a PyArrow-backed Parquet file at a configurable path (default `~/.local/share/tcal/events.parquet`).
- **Small modules** – `main.py` stays tiny, `orchestrator.py` owns top-level policy, leaf modules do one thing.

The detailed scope, non-goals, and roadmap live in [`PROJECTSCOPE.md`](./PROJECTSCOPE.md).

---

## Usage (current)

```bash
python main.py
```

You should see a placeholder screen with a header and a quit hint. Press `q` to exit. As features land, this section will expand with keybindings and workflows.

---

## Roadmap Snapshot

Short-term goals:

1. Parquet-backed storage module (PyArrow) with deterministic schema.
2. Month grid + day detail rendering.
3. Agenda list view with navigation.
4. External edit flow (`i`) that opens `$EDITOR` on a temp JSON (supports create when none selected).
5. Help overlay (`?`) describing keybindings.

Medium-term goals:

- Configurable keybindings via config file.
- Agenda-style rolling list view.
- Optional ICS import/export commands.

Out-of-scope for now: CalDAV/Google sync, notifications, natural-language assistants, background services.

---

## Development

- Entry: `python main.py`
- Python 3.11+
- Dependencies: `pyarrow`, `curses` (stdlib on Linux)
- Install: `pip install -r requirements.txt` (once present)

Structure mirrors other projects in this workspace:

```
tcal/
├─ main.py          # thin entrypoint
├─ orchestrator.py  # argument parsing + curses loop
├─ README.md
└─ PROJECTSCOPE.md
```

As functionality grows, expect small modules to appear alongside (`event_store.py`, `app_state.py`, etc.).
