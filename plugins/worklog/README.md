# worklog

1日の Claude Code セッションを横断して振り返り、再利用できる知識・自動化・Skill 候補を発見して、最も適切な置き場所へ分類するプラグインです。
価値が確認できた Skill は、同じプラグインの手順で社内マーケットプレイスへ登録します。

目的は「Skill を作ること」ではありません。
振り返りの結果、Skill が最適な保存形式だった場合にだけ Skill を作ります。
「本日の新規 Skill: なし」は正常な結果です。

## 提供するスキル

業務の流れに沿って `end → skill → publish` の順に使います。すべて手動起動です（Claude が自動で起動することはありません）。

| スキル | 起動 | 説明 |
|---|---|---|
| `end` | `/worklog:end [YYYY-MM-DD]` | 業務終了時に実行。対象日（省略時は今日）のセッションを集約して Daily Review を書き、再利用候補を分類・記録する |
| `skill` | `/worklog:skill [候補名 または 説明]` | 候補を作成判断チェックリストにかけ、個人（`~/.claude/skills/`）またはリポジトリ（`.claude/skills/`）に雛形から SKILL.md を書く |
| `publish` | `/worklog:publish <skill のディレクトリ> [マーケットプレイス clone のパス]` | 共有基準を確認し、マーケットプレイスの `plugins/` に複製、manifest 更新、validate、ブランチにコミットする。push と Pull Request は人が行う |

## Skill のライフサイクル

```
候補（~/.agent-worklog/candidates/skills.md）   ← /worklog:end が記録
  → 個人                                        ← /worklog:skill
  → リポジトリ                                   ← /worklog:skill
  → 社内                                        ← /worklog:publish → push と PR は人が行う
```

判断基準:

- `references/classification.md`: 見つけたものを docs / README / AGENTS.md / script / Skill 候補 / 何もしない のどこに置くか
- `references/skill-lifecycle.md`: Skill を作るか、社内共有するか、外部 Skill をどう扱うか
- `templates/SKILL-template.md`: Skill の雛形

## 前提

- `python3`（3.9 以上）と `git` が PATH にあること
- Claude Code の transcript が既定の場所（`~/.claude/projects/`、または `CLAUDE_CONFIG_DIR` 配下）にあること
- `publish` のみ: マーケットプレイスリポジトリの clone が手元にあり、作業ツリーがきれいであること

## 読む情報

- Claude Code の transcript（`~/.claude/projects/<cwd スラッグ>/<session_id>.jsonl`）
  - `cwd` / `gitBranch` / `timestamp` / セッション題名は transcript に含まれているため、別途 hook で記録しません
- 各リポジトリの `git log` / `git status` / `git diff` / `git worktree list`
- 各リポジトリの `README.md` / `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` / `docs/` / `scripts/`

## 書く場所

| スキル | 書く場所 |
|---|---|
| `end` | `~/.agent-worklog/daily/YYYY-MM-DD.md`、`~/.agent-worklog/candidates/{knowledge,automation,skills}.md`。docs / AGENTS.md / script への反映は提案として提示し、承認された場合にのみ書く |
| `skill` | 指定した skills ディレクトリと、`candidates/skills.md` の状態欄 |
| `publish` | マーケットプレイス clone 内の新しいブランチ。push はしない |

リポジトリへの自動書き込み、Pull Request の作成、外部通信はしません（GitBucket 環境では `gh` / `glab` 相当のツールがないため、コミットと PR は人が行います）。

## スクリプト

`scripts/sessions.py` は transcript を決定的に処理するための補助スクリプトです。`end` から呼ばれますが、単体でも使えます。

```
python3 scripts/sessions.py list [--date YYYY-MM-DD] [--json]
python3 scripts/sessions.py digest <session_id> [--max-chars N] [--per-message N]
```

- `list`: 対象日に記録のあるセッションを、リポジトリ（worktree なら元リポジトリも）ごとに一覧する
- `digest`: 1 セッションを「ユーザー発言 / Claude の応答 / 使用ツール / エラー」の可読テキストに変換する

## References

設計にあたり、次のプロジェクトを参考にしました。参考のみで、実行時の依存関係ではありません。

- [netresearch/retro-skill](https://github.com/netresearch/retro-skill)
  - 発見した学びを「唯一の正しい置き場所」へ流すという分類思想
  - 決定的処理（スクリプト）を先に走らせ、分類は LLM が行う層構造
  - hook は振り返りを自動実行せず、リマインドに留めるという判断
  - 提案ごとに Why / How-to-apply を示して個別に承認させる UX

## Why this is implemented internally

- 第三者プラグインを実行時依存にしない
- hook を使わず、読み取り専用のスクリプトと Markdown だけで構成し、監査しやすくする
- データの保存先を `~/.agent-worklog/` に限定し、外部送信を行わない
- 単位を「セッション」ではなく「1日・複数リポジトリ・複数 worktree」にする
- 社内の docs / README / AGENTS.md / script / Skill という分類ルールに合わせる
- Skill の共有に candidate → 個人 → リポジトリ → 社内 という昇格と PR レビューを設ける
