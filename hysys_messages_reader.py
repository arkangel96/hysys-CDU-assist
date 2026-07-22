"""
Read Aspen HYSYS continuous Messages pane (not modal popups).

The Messages window shows:
  - Left: Warnings / Optional Info (e.g. Temperature Cross)
  - Right: solver trace (Beginning Solution, Iter, Not Converged, invalid T, ...)

These are PE clues every time we run. Capture -> log -> tag for intelligence.

Strategy (two layers):
  1) COM probe on SimulationCase / Application for any Messages/Trace collection
  2) UI scrape of the visible "Messages" window owned by AspenHysys

Never auto-saves the .hsc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import win32gui
    import win32process

    _WIN = True
except ImportError:
    _WIN = False

from hysys_dialog_watcher import _is_hysys_process  # reuse process check

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "hysys_messages.log"

_LAST_MESSAGES: list["HysysMessageClue"] = []


@dataclass(slots=True)
class HysysMessageClue:
    timestamp: str
    source: str  # com | ui_left | ui_right
    text: str
    clue_tags: list[str] = field(default_factory=list)

    def summary(self) -> str:
        tags = ",".join(self.clue_tags) if self.clue_tags else "message"
        return f"[{tags}|{self.source}] {self.text}"


def classify_message_clue(text: str) -> list[str]:
    blob = text.lower()
    tags: list[str] = []
    if "temperature cross" in blob:
        tags.append("temperature_cross")
        tags.append("energy_or_feed")
    if "not converged" in blob:
        tags.append("not_converged")
        tags.append("numerical")
    if "converged" in blob and "not converged" not in blob:
        tags.append("converged_trace")
    if "invalid temperature" in blob:
        tags.append("invalid_temperature")
        tags.append("numerical")
        tags.append("poor_spec")
    if "poorly specified" in blob or "no solution" in blob:
        tags.append("poor_spec")
        tags.append("state_f_evidence")
    if "eqm error" in blob or "heat/spec error" in blob or "heat/spec" in blob:
        tags.append("solver_residuals")
    if "beginning solution" in blob:
        tags.append("solver_start")
    if "no sections" in blob and "internals" in blob:
        tags.append("internals_info")
    if "warning" in blob:
        tags.append("warning")
    if not tags:
        tags.append("hysys_message")
    return tags


def message_engineering_hint(tags: list[str], text: str) -> str:
    if "temperature_cross" in tags:
        return (
            "Messages: Temperature Cross on a heater/exchanger path — check "
            "duties/temps/feed heating; not a purity GoalValue issue."
        )
    if "invalid_temperature" in tags or "poor_spec" in tags:
        return (
            "Messages: invalid temperature / poorly specified — State B/A path; "
            "fix Active set or reverse last illegal Goal before more nudges."
        )
    if "not_converged" in tags:
        return "Messages: column not converged in trace — treat as numerical until green."
    if "solver_residuals" in tags:
        return "Messages: solver residual trace available — use with Monitor errors."
    return f"Messages clue: {text[:180]}"


def take_last_messages() -> list[HysysMessageClue]:
    return list(_LAST_MESSAGES)


def remember_messages(clues: list[HysysMessageClue]) -> None:
    global _LAST_MESSAGES
    _LAST_MESSAGES = list(clues)


def _ascii(text: object) -> str:
    return str(text).encode("ascii", "replace").decode()


def _append_log(line: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%H:%M:%S} {_ascii(line)}\n")
    except Exception:
        pass


def probe_messages_com(case: Any) -> list[HysysMessageClue]:
    """Best-effort COM discovery — HYSYS versions differ; may return empty."""
    clues: list[HysysMessageClue] = []
    if case is None:
        return clues
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    candidates = (
        "Messages",
        "MessageLog",
        "MessageManager",
        "Trace",
        "TraceWindow",
        "EventLog",
        "ActiveMessages",
        "FlowsheetMessages",
    )
    for name in candidates:
        try:
            obj = getattr(case, name)
        except Exception:
            continue
        if obj is None:
            continue
        # Try common collection patterns
        texts: list[str] = []
        try:
            count = int(obj.Count)
            for i in range(min(count, 40)):
                try:
                    item = obj.Item(i)
                except Exception:
                    try:
                        item = obj.Item(i + 1)
                    except Exception:
                        continue
                for attr in ("Message", "Text", "Description", "Name", "Value"):
                    try:
                        val = getattr(item, attr)
                        if val is not None and str(val).strip():
                            texts.append(str(val).strip())
                            break
                    except Exception:
                        continue
        except Exception:
            try:
                raw = str(obj)
                # Skip COM method stubs like "<bound method Trace of ...>"
                if "bound method" in raw.lower() or raw.startswith("<COMObject"):
                    continue
                texts.append(raw)
            except Exception:
                pass
        for text in texts[-20:]:
            tags = classify_message_clue(text)
            clues.append(
                HysysMessageClue(timestamp=ts, source=f"com:{name}", text=text, clue_tags=tags)
            )
    return clues


def _collect_window_texts(hwnd: int) -> list[str]:
    parts: list[str] = []

    def _enum(child: int, _) -> None:
        try:
            cls = win32gui.GetClassName(child).lower()
            if cls in {"static", "edit", "richedit", "richedit20w", "richedit50w", "listbox", "syslistview32"}:
                text = win32gui.GetWindowText(child).strip()
                if text:
                    parts.append(text)
                # ListBox: try LB_GETCOUNT / GETTEXT via SendMessage is heavier; skip for v1
        except Exception:
            pass

    try:
        win32gui.EnumChildWindows(hwnd, _enum, None)
    except Exception:
        pass
    return parts


def scrape_messages_ui() -> list[HysysMessageClue]:
    """Scrape visible Aspen HYSYS window titled Messages."""
    if not _WIN:
        return []
    found: list[tuple[int, str]] = []

    def _enum(hwnd: int, _) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        try:
            title = win32gui.GetWindowText(hwnd) or ""
        except Exception:
            return
        if title.strip().lower() != "messages":
            # sometimes "Messages - ..." 
            if not title.strip().lower().startswith("messages"):
                return
        try:
            _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            return
        if not _is_hysys_process(pid):
            return
        found.append((hwnd, title))

    win32gui.EnumWindows(_enum, None)
    clues: list[HysysMessageClue] = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for hwnd, _title in found:
        texts = _collect_window_texts(hwnd)
        # Also get recursive grandchild text via nested enum already in _collect
        blob = "\n".join(texts)
        if not blob.strip():
            continue
        # Split into useful lines
        for raw in blob.replace("\r", "\n").split("\n"):
            line = raw.strip()
            if len(line) < 8:
                continue
            low = line.lower()
            interesting = any(
                key in low
                for key in (
                    "warning",
                    "error",
                    "not converged",
                    "converged",
                    "temperature",
                    "invalid",
                    "iter:",
                    "eqm",
                    "heat/spec",
                    "beginning solution",
                    "optional info",
                    "poorly specified",
                )
            )
            if not interesting:
                continue
            source = "ui_left" if "warning" in low or "optional info" in low else "ui_right"
            tags = classify_message_clue(line)
            clues.append(
                HysysMessageClue(timestamp=ts, source=source, text=line, clue_tags=tags)
            )
    # de-dupe preserve order
    seen: set[str] = set()
    unique: list[HysysMessageClue] = []
    for clue in clues:
        key = clue.text
        if key in seen:
            continue
        seen.add(key)
        unique.append(clue)
    return unique[-40:]


def capture_hysys_messages(case: Any = None) -> list[HysysMessageClue]:
    """Capture COM + UI messages, log, remember for diagnose."""
    clues = probe_messages_com(case)
    clues.extend(scrape_messages_ui())
    # de-dupe by text
    seen: set[str] = set()
    merged: list[HysysMessageClue] = []
    for clue in clues:
        if clue.text in seen:
            continue
        seen.add(clue.text)
        merged.append(clue)
        _append_log(clue.summary())
    remember_messages(merged)
    return merged
