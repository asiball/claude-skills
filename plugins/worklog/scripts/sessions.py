#!/usr/bin/env python3
"""Claude Code の transcript (~/.claude/projects/**/*.jsonl) を決定的に処理する補助スクリプト。

  sessions.py list [--date YYYY-MM-DD] [--exclude SESSION_ID] [--json]
      対象日に記録のあるセッションをリポジトリごとに一覧する
  sessions.py digest <session_id> [--max-chars N] [--per-message N]
      1 セッションを可読テキスト（ユーザー発言 / 応答 / 使用ツール / エラー）に変換する
  sessions.py usage [--since YYYY-MM-DD] [--exclude SESSION_ID] [--json]
      Skill / スラッシュコマンドの呼び出し回数・最終使用日をまとめる（棚卸し用）

外部通信はしない。git は読み取りコマンド (rev-parse) のみ使う。
前提: transcript は手元の ~/.claude/projects/ にあるものだけを読む。Claude Code の
cleanupPeriodDays（既定 30 日）を過ぎた transcript は削除されているため、集計できる
期間には上限がある。usage はそのデータ範囲を必ず表示する。
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
LOCAL_COMMAND = re.compile(r"<local-command-(stdout|stderr|caveat)>.*?</local-command-\1>", re.DOTALL)
COMMAND_NAME = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
# Claude Code 組み込みコマンド。Skill ではないので usage に数えない
BUILTIN_COMMANDS = {
    "help", "clear", "compact", "model", "cost", "config", "init", "login", "logout", "doctor",
    "status", "memory", "review", "plugin", "mcp", "permissions", "resume", "exit", "quit", "vim",
    "terminal-setup", "bug", "release-notes", "add-dir", "agents", "hooks", "ide", "export",
    "context", "todos", "fast", "rewind", "skills", "keybindings", "statusline", "usage", "tasks",
}


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
    return LOCAL_COMMAND.sub("", SYSTEM_REMINDER.sub("", text)).strip()


def session_title(rec):
    """セッション題名を持つレコードなら題名を返す。"""
    if rec.get("type") == "custom-title" and rec.get("customTitle"):
        return str(rec["customTitle"])
    if rec.get("type") == "summary" and rec.get("summary"):
        return str(rec["summary"])
    if rec.get("aiTitle"):
        return str(rec["aiTitle"])
    return None


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"日付は YYYY-MM-DD 形式で指定してください: {value!r}")


def is_prompt(rec):
    return rec.get("type") == "user" and not rec.get("isSidechain") and bool(user_text(rec))


def skill_invocations(rec):
    """このレコードで呼び出された Skill / スラッシュコマンド名を (name, source) で返す。

    source は "command"（ユーザーが /name で起動）か "tool"（Claude が Skill ツールで起動）。
    <command-name> タグのないただの "/..." 発言は、タイプミスやパス言及と区別できないので数えない。
    サイドチェーン（サブエージェント）の記録は数えない。
    """
    if rec.get("isSidechain"):
        return []
    found = []
    if rec.get("type") == "user":
        for name in COMMAND_NAME.findall(user_text(rec)):
            found.append((name, "command"))
    elif rec.get("type") == "assistant":
        for b in content_blocks(rec):
            if b.get("type") == "tool_use" and b.get("name") == "Skill":
                inp = b.get("input") or {}
                if isinstance(inp, dict) and inp.get("skill"):
                    found.append((str(inp["skill"]).strip().lstrip("/"), "tool"))
    return [(n, src) for n, src in found if n and n not in BUILTIN_COMMANDS]


def prompt_title(text):
    """一覧表示用の 1 行目。スラッシュコマンド起動なら /name args の形に整える。"""
    m = COMMAND_NAME.search(text)
    if m:
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
        title = "/" + m.group(1)
        if args and args.group(1).strip():
            title += " " + args.group(1).strip()
        return title.splitlines()[0][:120]
    return text.splitlines()[0][:120]


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
    if cwd is None:
        info["note"] = "cwd not recorded in transcript"
    elif os.path.isdir(cwd):
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
        title = session_title(rec)
        if title:
            info["title"] = title
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
                info["first_prompt"] = prompt_title(user_text(rec))
    return info


def transcripts(exclude=None):
    """全 transcript のパス。exclude に指定した session_id は除く。"""
    for path in sorted(PROJECTS_DIR.glob("*/*.jsonl")):
        if exclude and path.stem == exclude:
            continue
        yield path


def cmd_list(args):
    day = args.date or date.today()
    if not PROJECTS_DIR.is_dir():
        sys.exit(f"transcript directory not found: {PROJECTS_DIR}")
    day_start = datetime.combine(day, datetime.min.time()).timestamp()
    sessions = []
    for path in transcripts(args.exclude):
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
            if s["cwd"] and s["cwd"] != key:
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
        title = session_title(rec)
        if title:
            meta["title"] = title
        if rec.get("isSidechain") or rec.get("type") not in ("user", "assistant"):
            continue
        ts = parse_ts(rec.get("timestamp"))
        if ts:
            meta["first"] = meta["first"] or ts
            if meta["last"] is None or ts.date() != meta["last"].date():
                lines.append(f"---- {ts:%Y-%m-%d} ----\n")
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


# ---------- usage ----------

def first_timestamp(path):
    for rec in iter_records(path):
        ts = parse_ts(rec.get("timestamp"))
        if ts:
            return ts
    return None


def cmd_usage(args):
    if not PROJECTS_DIR.is_dir():
        sys.exit(f"transcript directory not found: {PROJECTS_DIR}")
    since = args.since
    since_start = datetime.combine(since, datetime.min.time()).timestamp() if since else 0
    stats = {}
    oldest = None
    n_transcripts = 0
    for path in transcripts(args.exclude):
        n_transcripts += 1
        head = first_timestamp(path)
        if head and (oldest is None or head < oldest):
            oldest = head
        if path.stat().st_mtime < since_start:
            continue
        cwd = None
        pending_command = None  # ユーザーが /name で起動した直後に Claude が同名の Skill ツールを呼んだら 1 回に畳む
        for rec in iter_records(path):
            if rec.get("cwd"):
                cwd = rec["cwd"]
            if rec.get("type") == "user" and is_prompt(rec):
                pending_command = None
            hits = skill_invocations(rec)
            if not hits:
                continue
            ts = parse_ts(rec.get("timestamp"))
            if not ts or (since and ts.date() < since):
                continue
            for name, source in hits:
                if source == "tool" and name == pending_command:
                    continue
                if source == "command":
                    pending_command = name
                st = stats.setdefault(name, {"count": 0, "first": None, "last": None, "sessions": set(), "repos": set()})
                st["count"] += 1
                st["sessions"].add(path.stem)
                if cwd:
                    st["repos"].add(repo_info(cwd)["repo_root"] or cwd)
                st["first"] = ts if st["first"] is None or ts < st["first"] else st["first"]
                st["last"] = ts if st["last"] is None or ts > st["last"] else st["last"]

    rows = sorted(stats.items(), key=lambda kv: (-kv[1]["count"], kv[0]))
    data_from = oldest.date() if oldest else None
    covered_from = max(data_from, since) if (data_from and since) else (data_from or since)
    if args.json:
        out = {
            "transcripts": n_transcripts,
            "data_from": data_from.isoformat() if data_from else None,
            "since": since.isoformat() if since else None,
            "covered_from": covered_from.isoformat() if covered_from else None,
            "skills": [],
        }
        for name, st in rows:
            out["skills"].append({
                "skill": name,
                "count": st["count"],
                "sessions": len(st["sessions"]),
                "repos": sorted(st["repos"]),
                "first": st["first"].isoformat() if st["first"] else None,
                "last": st["last"].isoformat() if st["last"] else None,
            })
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    label = f"since {since.isoformat()}" if since else "all time"
    print(f"# skill usage ({label}): {len(rows)} skills")
    print(f"transcripts: {n_transcripts}, oldest record: {data_from.isoformat() if data_from else '-'}")
    if since and data_from and data_from > since:
        print(f"WARNING: transcripts older than {data_from.isoformat()} are gone (cleanupPeriodDays). "
              f"Actual coverage is {covered_from.isoformat()} to today; do not judge \"unused since {since.isoformat()}\" from this.")
    if not rows:
        return
    print()
    print(f"{'skill':<40} {'count':>5} {'sessions':>8} {'repos':>5}  {'first':<10} {'last':<10}")
    for name, st in rows:
        first = f"{st['first']:%Y-%m-%d}" if st["first"] else "-"
        last = f"{st['last']:%Y-%m-%d}" if st["last"] else "-"
        print(f"{name:<40} {st['count']:>5} {len(st['sessions']):>8} {len(st['repos']):>5}  {first:<10} {last:<10}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="対象日のセッション一覧")
    p.add_argument("--date", type=parse_date, help="YYYY-MM-DD (default: today)")
    p.add_argument("--exclude", metavar="SESSION_ID", help="除外するセッション（実行中の自分自身など）")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("digest", help="1 セッションの可読ダイジェスト")
    p.add_argument("session_id")
    p.add_argument("--max-chars", type=int, default=40000)
    p.add_argument("--per-message", type=int, default=600)
    p.set_defaults(func=cmd_digest)
    p = sub.add_parser("usage", help="Skill / スラッシュコマンドの使用実績")
    p.add_argument("--since", type=parse_date, help="YYYY-MM-DD (default: all transcripts)")
    p.add_argument("--exclude", metavar="SESSION_ID", help="除外するセッション（実行中の自分自身など）")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_usage)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
