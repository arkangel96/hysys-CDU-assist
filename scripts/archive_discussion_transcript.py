#!/usr/bin/env python3
"""Copy the latest Cursor agent transcript into docs/transcripts/ (git-friendly archive).

Does not modify HYSYS or Assist logic. Safe to re-run (skips if same file exists).

Usage (from repo root):
  path\\to\\.venv\\Scripts\\python.exe scripts/archive_discussion_transcript.py
  path\\to\\.venv\\Scripts\\python.exe scripts/archive_discussion_transcript.py --id 19ca8612-...
"""
from __future__ import annotations

import argparse
import os
import shutil
from datetime import date
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_transcripts_root() -> Path:
    # Cursor project cache (Windows). Override with CDU_AGENT_TRANSCRIPTS if needed.
    env = os.environ.get("CDU_AGENT_TRANSCRIPTS")
    if env:
        return Path(env)
    home = Path.home()
    return (
        home
        / ".cursor"
        / "projects"
        / "c-Users-USER-Documents-cdu-tool-cdu-tower-0723-night-hysys-CDU-assist"
        / "agent-transcripts"
    )


def _latest_session_dir(root: Path) -> Path | None:
    if not root.is_dir():
        return None
    dirs = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", help="Transcript folder / UUID to archive")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Agent-transcripts root (default: Cursor project cache)",
    )
    args = parser.parse_args()

    repo = _repo_root()
    src_root = args.source_root or _default_transcripts_root()
    if args.id:
        session = src_root / args.id
    else:
        session = _latest_session_dir(src_root)

    if session is None or not session.is_dir():
        print(f"No transcript session found under: {src_root}")
        return 1

    sid = session.name
    jsonl = session / f"{sid}.jsonl"
    if not jsonl.is_file():
        # some layouts nest once
        candidates = list(session.glob("*.jsonl"))
        if not candidates:
            print(f"No .jsonl in {session}")
            return 1
        jsonl = candidates[0]

    day = date.today().isoformat()
    dest_dir = repo / "docs" / "transcripts" / day
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / jsonl.name
    if dest.is_file():
        print(f"Already archived: {dest.relative_to(repo)}")
    else:
        shutil.copy2(jsonl, dest)
        print(f"Archived: {dest.relative_to(repo)}")

    readme = repo / "docs" / "transcripts" / "README.md"
    line = f"| {day} | [`{day}/{jsonl.name}`]({day}/{jsonl.name}) | Auto-archive via scripts/archive_discussion_transcript.py |\n"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if jsonl.name not in text:
            # Insert after table header row block — append near top of table
            marker = "| Date | File | Notes |\n|------|------|--------|\n"
            if marker in text:
                text = text.replace(marker, marker + line, 1)
                readme.write_text(text, encoding="utf-8")
                print("Updated docs/transcripts/README.md index")
            else:
                print("README table marker not found — copy path manually into index")
    print("Also update docs/DISCUSSION_LOG.md with a short bullet summary if not done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
