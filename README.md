# tcal

Tcal is a **Vim-first, terminal-native calendar** for folks who live in Vim and want a fast way to browse days, weeks, and months without leaving the terminal. It is written in Python using `curses`, keeps a flat project layout, and mirrors the thin-`main.py`/central-`orchestrator.py` pattern used across my other tools.

---

## Status

🚧 Early scaffolding. The current build boots a placeholder curses screen to prove out the control flow. Event storage, navigation, and editing flows are next.

---

## Philosophy

- **Keyboard supreme** – every action is reachable with predictable, Vim-inspired bindings.
- **Terminal-native** – no GUI toolkits, no mouse assumptions, no background daemons.
- **Transparent storage** – events live in a human-readable JSON file under `$XDG_CONFIG_HOME/tcal` (fallback `~/.config/tcal`).
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

1. Event storage module (JSON-based) with deterministic schema.
2. Month grid + day detail rendering.
3. Event create/edit/delete flows with inline forms.
4. Help overlay (`?`) describing keybindings.

Medium-term goals:

- Configurable keybindings via config file.
- Agenda-style rolling list view.
- Optional ICS import/export commands.

Out-of-scope for now: CalDAV/Google sync, notifications, natural-language assistants, background services.

---

## Development

- Entry: `python main.py`
- Python 3.11+
- Dependencies: stdlib only for now (`curses` ships with Python on Linux).

Structure mirrors other projects in this workspace:

```
tcal/
├─ main.py          # thin entrypoint
├─ orchestrator.py  # argument parsing + curses loop
├─ README.md
└─ PROJECTSCOPE.md
```

As functionality grows, expect small modules to appear alongside (`event_store.py`, `app_state.py`, etc.).
