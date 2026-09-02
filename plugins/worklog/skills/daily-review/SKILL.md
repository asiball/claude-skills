---
name: daily-review
description: 1日の Claude Code セッションを横断して振り返り、Daily Review を書き、再利用候補を docs / README / AGENTS.md / script / Skill に分類する。業務終了時に手動で実行する。
argument-hint: "[YYYY-MM-DD]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash(git log *)
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git show *)
  - Bash(git worktree list *)
---

# Daily Review

対象日のセッションを集約して 1 日を振り返り、再利用できるものを最も適切な置き場所へ残す。

## 原則

- 目的は Skill を作ることではない。「Skill 候補: なし」は正常かつ望ましい結果として扱う
- 推測しない。サマリだけで判断せず、transcript・git・リポジトリの実ファイルを確認する
- リポジトリには勝手に書き込まない。反映は提案として提示し、承認された場合にのみ行う
- Pull Request は作らない。コミットと PR は人が行う
- 一度きりの情報は記録しない。記録コストの方が高いものは「何もしない」を選ぶ
- 外部通信をしない

## 対象日

`$ARGUMENTS` に `YYYY-MM-DD` があればその日、なければ今日。以下 `<date>` と書く。

## 手順

### 1. セッションを列挙する

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sessions.py list --date <date>
```

- リポジトリ（worktree の場合は元リポジトリも）ごとにセッションが並ぶ
- この Daily Review を実行している現在のセッション自身は対象から外す
- セッションが 1 つもなければ、`~/.agent-worklog/daily/<date>.md` に「セッションなし」とだけ書いて終了する

### 2. 各セッションの内容を読む

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sessions.py digest <session_id>
```

セッションごとに把握すること: 何を頼まれ、何をして、何が終わり、何が終わっていないか。繰り返し同じ説明・同じ手順・同じ失敗が出ていないか。
ダイジェストが切り詰められていて判断がつかない場合は `--max-chars` を増やすか、transcript を直接読む。

### 3. リポジトリの実情報を確認する

セッションが属するリポジトリごとに、必要な範囲で確認する。

- `git -C <root> log --since="<date> 00:00" --until="<date> 23:59" --stat`
- `git -C <root> status --short` と `git -C <root> diff --stat`（未コミットの作業）
- `git -C <root> worktree list`
- `README.md` / `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` / `docs/` / `scripts/` の有無と、今日の作業に関係する記述

「新しく得られた知識」が既にどこかに書かれていないかは、ここで必ず確認する。

### 4. 再利用候補を分類する

発見したものを `references/classification.md` の基準で振り分ける。
判断に迷うものは「何もしない」か「候補として保留」に倒す。

### 5. Daily Review を書く

`~/.agent-worklog/daily/<date>.md` に以下の見出しで書く（ディレクトリがなければ作る）。
既にファイルがある場合は内容を読み、上書きしてよいか確認してから書く。

```markdown
# Daily Review <date>

## 今日やったこと
（リポジトリ / worktree ごとに箇条書き。セッション ID を添える）

## 完了したこと

## 未完了・継続中

## 次回の開始地点
（リポジトリ・ブランチ・着手すべき具体的な作業）

## 新しく得られた知識

## 開発環境・作業フローの改善候補

## 再利用候補
（分類結果。項目ごとに 置き場所 / 理由 / 対象リポジトリ）

## docs / AGENTS.md / CLAUDE.md / script への反映候補

## Skill 候補
（なければ「Skill 候補: なし」）
```

### 6. 候補ファイルを更新する

`~/.agent-worklog/candidates/` の該当ファイルに追記する。

| ファイル | 内容 |
|---|---|
| `knowledge.md` | docs / README / CONTRIBUTING / AGENTS.md / CLAUDE.md への反映候補 |
| `automation.md` | script 化の候補 |
| `skills.md` | Skill 候補（状態: candidate） |

エントリの形式:

```markdown
## <候補名>

- 初回検出: <date>
- 再検出: （再発した日付を追記）
- 対象: <リポジトリ / 個人 / 社内>
- 概要: 何をどう行う手順・知識か
- 候補になった理由:
- 状態: candidate | applied | rejected
```

同じ候補が既にある場合は新規に作らず「再検出」に日付を追記し、再評価する。
「N 回で必ず Skill 化」のような固定ルールは使わない。再発回数は判断材料の一つに留める。

### 7. 反映を提案する

Daily Review に書いた反映候補のうち、今すぐ価値があるものを提案する。
提案ごとに **なぜ** と **どこにどう書くか** を示し、承認されたものだけ実行する。

- docs / README / CONTRIBUTING / AGENTS.md / CLAUDE.md: 既存の正本と重複させない。正本があれば参照を書く
- script: 決定的な処理のみ。Skill にしない
- Skill: ここでは作らない。`candidates/skills.md` に候補として残し、作成する場合は `/skill-kit:create <候補名>` を案内する

### 8. 結果を報告する

最後に、書いたファイル・更新した候補・承認されて反映したもの・見送ったものを短く一覧にする。
