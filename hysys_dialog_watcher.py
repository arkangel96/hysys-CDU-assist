"""
HYSYS dialog watcher — capture popup text as engineering clues, then act.

Popups (MessageBox / #32770) often explain invalid specs, draw>feed, solver
issues, etc. Assist must:
  1) SEE  — read title + body text
  2) LOG  — persist for the PE board / audit
  3) ACT  — map clue -> diagnosis hint; optionally click OK so multi-run continues

Never auto-saves the .hsc.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    import win32api
    import win32con
    import win32gui
    import win32process

    _WIN = True
except ImportError:  # non-Windows / missing pywin32
    _WIN = False


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "hysys_dialogs.log"

# Process name fragments that own HYSYS UI dialogs
_HYSYS_PROC = ("aspenhysys", "hysys")


@dataclass(slots=True)
class HysysDialogClue:
    """One HYSYS popup — treated as engineering evidence."""

    timestamp: str
    title: str
    message: str
    hwnd: int
    dismissed: bool = False
    clue_tags: list[str] = field(default_factory=list)

    def summary(self) -> str:
        tags = ",".join(self.clue_tags) if self.clue_tags else "general"
        return f"[{tags}] {self.title}: {self.message}"


def classify_dialog_clue(title: str, message: str) -> list[str]:
    """Map popup text to PE clue tags (intelligence input)."""
    blob = f"{title}\n{message}".lower()
    tags: list[str] = []

    if "invalid spec" in blob or "invalid spec value" in blob:
        tags.append("invalid_spec")
    if "draw rate must be less than the total feed" in blob or (
        "draw rate" in blob and "feed" in blob
    ):
        tags.append("draw_exceeds_feed")
        tags.append("split_family")
    if "ratio spec" in blob and "recycle" in blob:
        tags.append("prefer_ratio_spec")
    if "degree" in blob and "freedom" in blob:
        tags.append("dof")
    if "not converged" in blob or "failed to converge" in blob:
        tags.append("convergence")
    if "estimate" in blob:
        tags.append("estimates")
    if "overflow" in blob or "singular" in blob:
        tags.append("numerical")
    if "temperature" in blob and ("cross" in blob or "invalid" in blob):
        tags.append("profile")
    if not tags:
        tags.append("hysys_warning")
    return tags


def clue_to_preferred_family(tags: list[str]) -> str:
    if "draw_exceeds_feed" in tags or "split_family" in tags:
        return "C_split"
    if "estimates" in tags or "numerical" in tags or "convergence" in tags:
        return "A_init"
    if "dof" in tags or "invalid_spec" in tags:
        return "A_init"
    return ""


def clue_engineering_hint(tags: list[str], message: str) -> str:
    if "draw_exceeds_feed" in tags:
        return (
            "HYSYS popup: overhead/draw Goal exceeds feed — illegal split. "
            "Prefer C_split (lower Ovhd / restore Btms Active); do not keep raising draw."
        )
    if "invalid_spec" in tags:
        return f"HYSYS popup: invalid specification — fix Active Goal/spec set. ({message[:160]})"
    if "dof" in tags:
        return "HYSYS popup: degrees-of-freedom / spec set issue — State A path."
    if "numerical" in tags or "convergence" in tags:
        return "HYSYS popup: numerical/convergence warning — State B recovery first."
    if "estimates" in tags:
        return "HYSYS popup: estimates — refresh/use estimates before more Goal nudges."
    return f"HYSYS popup clue: {message[:200]}"


def _process_name(pid: int) -> str:
    if not _WIN:
        return ""
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
        )
        try:
            return str(win32process.GetModuleFileNameEx(handle, 0)).lower()
        finally:
            win32api.CloseHandle(handle)
    except Exception:
        return ""


def _is_hysys_process(pid: int) -> bool:
    name = _process_name(pid)
    return any(token in name for token in _HYSYS_PROC)


def _dialog_message_text(hwnd: int) -> str:
    """Collect Static / text control captions inside a dialog."""
    parts: list[str] = []

    def _enum(child: int, _) -> None:
        try:
            cls = win32gui.GetClassName(child)
            if cls.lower() in {"static", "richedit", "richedit20w", "edit"}:
                text = win32gui.GetWindowText(child).strip()
                if text and text not in parts:
                    parts.append(text)
        except Exception:
            pass

    try:
        win32gui.EnumChildWindows(hwnd, _enum, None)
    except Exception:
        pass
    return " | ".join(parts) if parts else ""


def _find_ok_button(hwnd: int) -> int | None:
    found: list[int] = []

    def _enum(child: int, _) -> None:
        try:
            if win32gui.GetClassName(child).lower() != "button":
                return
            label = win32gui.GetWindowText(child).replace("&", "").strip().lower()
            if label in {"ok", "yes", "continue", "close"}:
                found.append(child)
        except Exception:
            pass

    try:
        win32gui.EnumChildWindows(hwnd, _enum, None)
    except Exception:
        pass
    return found[0] if found else None


def _click_button(button_hwnd: int) -> bool:
    try:
        win32gui.SendMessage(button_hwnd, win32con.BM_CLICK, 0, 0)
        return True
    except Exception:
        try:
            win32gui.PostMessage(button_hwnd, win32con.BM_CLICK, 0, 0)
            return True
        except Exception:
            return False


@dataclass
class HysysDialogWatcher:
    """Background watcher: SEE popup clues, LOG them, optionally dismiss OK."""

    auto_dismiss: bool = True
    poll_s: float = 0.35
    log_path: Path = LOG_FILE
    on_clue: Callable[[HysysDialogClue], None] | None = None

    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    _seen: set[int] = field(default_factory=set, init=False)
    clues: list[HysysDialogClue] = field(default_factory=list, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def start(self) -> None:
        if not _WIN:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(
            target=self._loop, name="HysysDialogWatcher", daemon=True
        )
        self._thread.start()

    def stop(self) -> list[HysysDialogClue]:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            return list(self.clues)

    def __enter__(self) -> "HysysDialogWatcher":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def snapshot_clues(self) -> list[HysysDialogClue]:
        with self._lock:
            return list(self.clues)

    def format_clues_for_pe_board(self) -> str:
        with self._lock:
            if not self.clues:
                return ""
            lines = ["HYSYS POPUP CLUES (from dialogs during run):"]
            for clue in self.clues[-8:]:
                hint = clue_engineering_hint(clue.clue_tags, clue.message)
                lines.append(f"  • {_ascii(clue.summary())}")
                lines.append(f"    -> {_ascii(hint)}")
            return "\n".join(lines)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._scan_once()
            except Exception as exc:
                self._append_log(f"watcher_error: {exc}")
            time.sleep(self.poll_s)

    def _scan_once(self) -> None:
        if not _WIN:
            return

        def _enum(hwnd: int, _) -> None:
            if not win32gui.IsWindowVisible(hwnd):
                return
            try:
                cls = win32gui.GetClassName(hwnd)
            except Exception:
                return
            if cls != "#32770":
                return
            if hwnd in self._seen:
                return
            try:
                _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                return
            if not _is_hysys_process(pid):
                return

            title = win32gui.GetWindowText(hwnd) or "Aspen HYSYS"
            message = _dialog_message_text(hwnd) or "(no static text)"
            tags = classify_dialog_clue(title, message)
            dismissed = False
            if self.auto_dismiss:
                btn = _find_ok_button(hwnd)
                if btn is not None:
                    dismissed = _click_button(btn)

            clue = HysysDialogClue(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                title=title,
                message=message,
                hwnd=int(hwnd),
                dismissed=dismissed,
                clue_tags=tags,
            )
            self._seen.add(hwnd)
            with self._lock:
                self.clues.append(clue)
            self._append_log(clue.summary() + (f" dismissed={dismissed}"))
            if self.on_clue is not None:
                try:
                    self.on_clue(clue)
                except Exception:
                    pass

        win32gui.EnumWindows(_enum, None)

    def _append_log(self, line: str) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now():%H:%M:%S} {_ascii(line)}\n")
        except Exception:
            pass


def _ascii(text: object) -> str:
    return str(text).encode("ascii", "replace").decode()


# Process-wide last clues (so diagnose/PE board can read after a run)
_LAST_CLUES: list[HysysDialogClue] = []


def take_last_clues() -> list[HysysDialogClue]:
    return list(_LAST_CLUES)


def remember_clues(clues: list[HysysDialogClue]) -> None:
    global _LAST_CLUES
    _LAST_CLUES = list(clues)


def run_with_dialog_awareness(fn, *, auto_dismiss: bool = True):
    """Run callable while watching HYSYS dialogs; return (result, clues)."""
    watcher = HysysDialogWatcher(auto_dismiss=auto_dismiss)
    watcher.start()
    try:
        result = fn()
    finally:
        clues = watcher.stop()
        remember_clues(clues)
    return result, clues
