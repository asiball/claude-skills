#!/usr/bin/env python3
"""Claude Code の transcript (~/.claude/projects/**/*.jsonl) を決定的に処理する補助スクリプト。

  sessions.py list [--date YYYY-MM-DD] [--json]
      対象日に記録のあるセッションをリポジトリごとに一覧する
  sessions.py digest <session_id> [--max-chars N] [--per-message N]
      1 セッションを可読テキスト（ユーザー発言 / 応答 / 使用ツール / エラー）に変換する

外部通信はしない。git は読み取りコマンド (rev-parse) のみ使う。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
PROJECTS_DIR = CONFIG_DIR / "projects"
SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def iter_records(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def content_blocks(rec):
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def user_text(rec):
    parts = [b.get("text", "") for b in content_blocks(rec) if b.get("type") == "text"]
    text = "\n".join(parts)
    return SYSTEM_REMINDER.sub("", text).strip()


def is_prompt(rec):
    return rec.get("type") == "user" and not rec.get("isSidechain") and bool(user_text(rec))


# ---------- git ----------

_repo_cache = {}


def git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None


def repo_info(cwd):
    if cwd in _repo_cache:
        return _repo_cache[cwd]
    info = {"repo_root": None, "main_repo": None}
    if cwd and os.path.isdir(cwd):
        root = git(cwd, "rev-parse", "--show-toplevel")
        if root:
            info["repo_root"] = root
            common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
            if common and os.path.basename(common) == ".git":
                main_dir = os.path.dirname(common)
                if os.path.realpath(main_dir) != os.path.realpath(root):
                    info["main_repo"] = main_dir
    else:
        info["note"] = "cwd not found (worktree removed?)"
    _repo_cache[cwd] = info
    return info


# ---------- list ----------

def scan_session(path, day):
    info = {
        "session_id": path.stem,
        "transcript": str(path),
        "cwd": None,
        "branch": None,
        "title": None,
        "first": None,
        "last": None,
        "prompts": 0,
        "prompts_on_day": 0,
        "first_prompt": None,
    }
    for rec in iter_records(path):
        if rec.get("cwd"):
            info["cwd"] = rec["cwd"]
        if rec.get("gitBranch"):
            info["branch"] = rec["gitBranch"]
        if rec.get("aiTitle"):
            info["title"] = rec["aiTitle"]
        ts = parse_ts(rec.get("timestamp"))
        if not ts:
            continue
        prompt = is_prompt(rec)
        if prompt:
            info["prompts"] += 1
        if ts.date() != day:
            continue
        info["first"] = info["first"] or ts
        info["last"] = ts
        if prompt:
            info["prompts_on_day"] += 1
            if info["first_prompt"] is None:
                info["first_prompt"] = user_text(rec).splitlines()[0][:120]
    return info


def cmd_list(args):
    day = date.fromisoformat(args.date) if args.date else date.today()
    if not PROJECTS_DIR.is_dir():
        sys.exit(f"transcript directory not found: {PROJECTS_DIR}")
    day_start = datetime.combine(day, datetime.min.time()).timestamp()
    sessions = []
    for path in PROJECTS_DIR.glob("*/*.jsonl"):
        if path.stat().st_mtime < day_start:
            continue  # 対象日より前に最終更新 → 対象日の記録はない
        info = scan_session(path, day)
        if info["first"] is None or info["prompts"] == 0:
            continue
        info.update(repo_info(info["cwd"]))
        sessions.append(info)
    sessions.sort(key=lambda s: s["first"])

    if args.json:
        out = []
        for s in sessions:
            d = dict(s)
            d["first"] = s["first"].isoformat()
            d["last"] = s["last"].isoformat()
            out.append(d)
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    print(f"# sessions on {day.isoformat()}: {len(sessions)}")
    if not sessions:
        return
    groups = {}
    for s in sessions:
        key = s["repo_root"] or s["cwd"] or "(unknown)"
        groups.setdefault(key, []).append(s)
    for key, items in groups.items():
        print()
        print(f"## {key}")
        main = items[0].get("main_repo")
        if main:
            print(f"   worktree of: {main}")
        if items[0].get("note"):
            print(f"   note: {items[0]['note']}")
        for s in items:
            span = f"{s['first']:%H:%M}-{s['last']:%H:%M}"
            branch = s["branch"] or "-"
            title = s["title"] or s["first_prompt"] or ""
            print(f"- {span}  {s['session_id']}  branch={branch}  prompts={s['prompts_on_day']}/{s['prompts']}")
            if title:
                print(f"    {title}")
            if s["cwd"] != key:
                print(f"    cwd: {s['cwd']}")


# ---------- digest ----------

def find_transcript(session_id):
    for path in PROJECTS_DIR.glob(f"*/{session_id}.jsonl"):
        return path
    sys.exit(f"transcript not found for session {session_id}")


def brief_input(name, inp):
    if not isinstance(inp, dict):
        return ""
    for key in ("command", "file_path", "pattern", "prompt", "query", "url", "skill"):
        if key in inp:
            return str(inp[key]).replace("\n", " ")[:160]
    return json.dumps(inp, ensure_ascii=False)[:160]


def clip(text, limit):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f" …(+{len(text) - limit} chars)"


def cmd_digest(args):
    path = find_transcript(args.session_id)
    lines = []
    meta = {"cwd": None, "branch": None, "title": None, "first": None, "last": None}
    tools = {}

    for rec in iter_records(path):
        if rec.get("cwd"):
            meta["cwd"] = rec["cwd"]
        if rec.get("gitBranch"):
            meta["branch"] = rec["gitBranch"]
        if rec.get("aiTitle"):
            meta["title"] = rec["aiTitle"]
        if rec.get("isSidechain") or rec.get("type") not in ("user", "assistant"):
            continue
        ts = parse_ts(rec.get("timestamp"))
        if ts:
            meta["first"] = meta["first"] or ts
            meta["last"] = ts
        stamp = f"[{ts:%H:%M}]" if ts else "[--:--]"

        if rec.get("type") == "user":
            text = user_text(rec)
            if text:
                lines.append(f"{stamp} USER:\n{clip(text, args.per_message)}\n")
            for b in content_blocks(rec):
                if b.get("type") == "tool_result" and b.get("is_error"):
                    c = b.get("content")
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    lines.append(f"    RESULT(error): {clip(str(c or ''), 300)}\n")
        else:
            for b in content_blocks(rec):
                if b.get("type") == "text" and b.get("text", "").strip():
                    lines.append(f"{stamp} ASSISTANT:\n{clip(b['text'], args.per_message)}\n")
                elif b.get("type") == "tool_use":
                    name = b.get("name", "?")
                    tools[name] = tools.get(name, 0) + 1
                    lines.append(f"    TOOL {name}: {brief_input(name, b.get('input'))}\n")

    header = [
        f"# session {args.session_id}",
        f"transcript: {path}",
        f"cwd: {meta['cwd']}",
        f"branch: {meta['branch']}",
        f"title: {meta['title']}",
        f"time: {meta['first']:%Y-%m-%d %H:%M} - {meta['last']:%Y-%m-%d %H:%M}" if meta["first"] else "time: -",
        "tools: " + ", ".join(f"{k}={v}" for k, v in sorted(tools.items(), key=lambda kv: -kv[1])),
        "",
    ]
    body = "\n".join(lines)
    if len(body) > args.max_chars:
        body = body[: args.max_chars] + f"\n\n…(digest truncated at {args.max_chars} chars; {len(body)} total)"
    print("\n".join(header) + body)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="対象日のセッション一覧")
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("digest", help="1 セッションの可読ダイジェスト")
    p.add_argument("session_id")
    p.add_argument("--max-chars", type=int, default=40000)
    p.add_argument("--per-message", type=int, default=600)
    p.set_defaults(func=cmd_digest)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
