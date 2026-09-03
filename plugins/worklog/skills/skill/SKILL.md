---
name: skill
description: Skill 候補から Skill を作成する。作成判断チェックリストを通し、個人またはリポジトリの skills ディレクトリに雛形から SKILL.md を書く。
argument-hint: "[候補名 または 説明]"
disable-model-invocation: true
---

# Skill を作成する

候補を作成判断にかけ、通ったものだけを雛形から作る。作らない判断も正常な結果。

## 手順

### 1. 対象を特定する

- `$ARGUMENTS` が候補名なら `~/.agent-worklog/candidates/skills.md` の該当エントリを読む
- 候補名でなければ説明として扱う。足りなければユーザーに聞く: 何を、どんな判断で、どのくらいの頻度で行うか

### 2. 作成判断をする

`${CLAUDE_PLUGIN_ROOT}/references/skill-lifecycle.md` の「Skill 作成判断」7 項目を 1 つずつ確認し、結果を表で示す。

既存 Skill の確認は実際に見る:

- 個人: `ls ~/.claude/skills/`
- リポジトリ: `ls <repo>/.claude/skills/`
- 社内: マーケットプレイスの `plugins/*/skills/`（clone があれば）

script / docs / AGENTS.md で足りると判断したら、その代替案を示して終了する。候補ファイルの状態は `rejected` にし、理由を残す。

### 3. 置き場所を決める

ユーザーに確認する。

| 置き場所 | パス | 条件 |
|---|---|---|
| 個人 | `~/.claude/skills/<name>/SKILL.md` | まず自分で使って価値を確かめる段階 |
| リポジトリ | `<repo>/.claude/skills/<name>/SKILL.md` | そのリポジトリの作業者全員に必要 |

社内共有はここでは行わない。運用して価値が確認できたら `/worklog:publish` を使う。

### 4. 設計する

- `name`: kebab-case。動詞または「対象-動詞」で、何をするかが分かる名前
- `description`: 何をするかと、いつ使うかを先頭に。1〜2 文
- 起動方法: 副作用がある、または手動で使いたいなら `disable-model-invocation: true`
- `allowed-tools`: 読み取り系の最小限。書き込み系は入れない
- 同梱するもの: 決定的な処理は `scripts/` に、長い参考資料は `references/` に分けて SKILL.md を短く保つ

### 5. 雛形から書く

`${CLAUDE_PLUGIN_ROOT}/templates/SKILL-template.md` を元に、全セクションを埋める。該当しないセクションは削除せず「該当なし」と書く。
候補エントリの「概要」「候補になった理由」を Purpose と When to use に反映する。

### 6. 確認する

skills ディレクトリはセッション中に監視されているので、作成直後から `/<name>` で使える。
ユーザーに一度実行してもらい、手順が実態に合っているかを確認する。ずれがあれば直す。

### 7. 候補の状態を更新する

`~/.agent-worklog/candidates/skills.md` の該当エントリに追記する:

- 状態: `applied`
- 作成先: パス
- 作成日

### 8. 報告する

作成したパス、起動名、次にやること（数回使って価値を確かめる → 必要なら `/worklog:publish`）を短く示す。
