"""Help and cheatsheet content for the xyz TUI."""

from __future__ import annotations

HELP_LINES: tuple[str, ...] = (
    "Guidance",
    "",
    "If x ≈ 3-month goals, y/z should feel realistic and grounded.",
    "If x ≈ 5-year goals, y/z should feel expansive yet meaningful.",
    "If x ≈ lifetime goals, y/z should feel deeply values-driven.",
    "",
    "p/q/r scores: 0–10 scale (allow decimals).",
    "  • p = How aligned was this with Jesus-like values: love, truth, humility, stewardship?",
    "  • q = What good did it create in the world around you: work, family, service, finances?",
    "  • r = What good did it create in the world around you: work, family, service, finances?",
    "",
    "Shortcuts",
    "",
    "q            quit",
    "?            toggle this help",
    "t            jump to today",
    "i            edit/create event",
    "dd           delete selected event",
    "hjkl         navigate (agenda/month)",
    "B            agenda: edit bucket of selected task",
    ",xr          agenda: toggle expand/collapse current row",
    "Ctrl+h/l     month view: prev/next month",
    "Ctrl+j/k     month view: next/prev year",
    "a            toggle agenda/month",
    "Tab          cycle buckets (agenda & month)",
    "Enter        month view: move focus grid ↔ tasks",
    "Esc          dismiss overlays",
)

__all__ = ["HELP_LINES"]
