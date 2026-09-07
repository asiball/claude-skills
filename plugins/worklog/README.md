# worklog

1日の Claude Code セッションを横断して振り返り、再利用できる知識・自動化・Skill 候補を発見して、最も適切な置き場所へ分類するプラグインです。
価値が確認できた Skill は、同じプラグインの手順で社内マーケットプレイスへ登録します。

目的は「Skill を作ること」ではありません。
振り返りの結果、Skill が最適な保存形式だった場合にだけ Skill を作ります。
「本日の新規 Skill: なし」は正常な結果です。

## 提供するスキル

毎日 `end` を実行し、必要が出たときに `tidy` か `publish` を使います。すべて手動起動です（Claude が自動で起動することはありません）。

| スキル | 起動 | 頻度 | 説明 |
|---|---|---|---|
| `end` | `/worklog:end [YYYY-MM-DD] [候補名]` | 毎日 | 業務終了時に実行。対象日（省略時は今日）のセッションを集約して Daily Review を書き、再利用候補を分類・記録する。再検出された Skill 候補（または候補名で指定したもの）は作成判断にかけ、通れば個人（`~/.claude/skills/`）またはリポジトリ（`.claude/skills/`）に雛形から SKILL.md を書く |
| `tidy` | `/worklog:tidy [マーケットプレイス clone のパス]` | 週 1 か月 1 | 候補・個人やリポジトリの Skill・社内公開済み Skill を棚卸しする。使用実績と最終確認日を集計し、放置された候補の整理、未使用 Skill の削除や昇格、最終確認日の更新を提案する |
| `publish` | `/worklog:publish <skill のディレクトリ> [マーケットプレイス clone のパス]` | 必要時 | 共有基準を確認し、マーケットプレイスの `plugins/` に複製、manifest 更新、validate、ブランチにコミットする。push と Pull Request は人が行う |

Skill の作成を `end` に含めているのは、transcript を読み終えた直後が手順の実態を最もよく把握している瞬間だからです。ただし初回検出の候補はその日に作らず、再検出されたものを作成対象にします。今すぐ作りたい候補は `/worklog:end <候補名>` で指定します。

## Skill のライフサイクル

```
候補（~/.agent-worklog/candidates/skills.md）   ← /worklog:end が記録
  → 個人                                        ← /worklog:end が再検出時に作成（置き場所は作成時に選ぶ）
  → リポジトリ                                   ← 同上
  → 社内                                        ← /worklog:publish → push と PR は人が行う
  各段階の見直し・削除                             ← /worklog:tidy が定期的に提案
```

判断基準:

- `references/classification.md`: 見つけたものを docs / README / AGENTS.md / script / Skill 候補 / 何もしない のどこに置くか
- `references/skill-lifecycle.md`: Skill を作るか、社内共有するか、外部 Skill をどう扱うか
- `references/skill-creation.md`: 作成判断チェックリストから雛形での作成までの手順（`end` から参照）
- `templates/SKILL-template.md`: Skill の雛形

## 前提

- `python3`（3.9 以上）と `git` が PATH にあること
- Claude Code の transcript が既定の場所（`~/.claude/projects/`、または `CLAUDE_CONFIG_DIR` 配下）にあること
- `publish` のみ: マーケットプレイスリポジトリの clone が手元にあり、作業ツリーがきれいであること

## 読む情報

- Claude Code の transcript（`~/.claude/projects/<cwd スラッグ>/<session_id>.jsonl`）
  - `cwd` / `gitBranch` / `timestamp` / セッション題名（`custom-title` レコード）は transcript に含まれているため、別途 hook で記録しません
  - transcript は Claude Code の `cleanupPeriodDays`（既定 30 日）で削除されるため、`tidy` の使用実績はその範囲内に限られます。スクリプトは実データの範囲を表示します
  - 対象日の絞り込みにファイルの更新日時を使うため、transcript をコピー・復元して更新日時が変わった場合は一覧から漏れることがあります
- 各リポジトリの `git log` / `git status` / `git diff` / `git worktree list`
- 各リポジトリの `README.md` / `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` / `docs/` / `scripts/`

## 書く場所

| スキル | 書く場所 |
|---|---|
| `end` | `~/.agent-worklog/daily/YYYY-MM-DD.md`、`~/.agent-worklog/candidates/{knowledge,automation,skills}.md`。docs / AGENTS.md / script への反映と Skill の作成は提案として提示し、承認された場合にのみ書く |
| `tidy` | `~/.agent-worklog/tidy/YYYY-MM-DD.md`（提案と決定の記録）、`candidates/*.md` の状態欄。Skill の削除・更新は承認された場合にのみ行い、リポジトリや clone のコミットは人が行う |
| `publish` | マーケットプレイス clone 内の新しいブランチ。push はしない |

`~/.agent-worklog/` は隠しディレクトリです。Daily Review は 1 日 1 ファイル数 KB 程度で、`end` が読み返すのは当日分と `candidates/*.md` だけです。`tidy` が件数とサイズを報告します。

リポジトリへの自動書き込み、Pull Request の作成、外部通信はしません（GitBucket 環境では `gh` / `glab` 相当のツールがないため、コミットと PR は人が行います）。

## スクリプト

`scripts/sessions.py` は transcript を決定的に処理するための補助スクリプトです。`end` と `tidy` から呼ばれますが、単体でも使えます。

```
python3 scripts/sessions.py list [--date YYYY-MM-DD] [--exclude SESSION_ID] [--json]
python3 scripts/sessions.py digest <session_id> [--max-chars N] [--per-message N]
python3 scripts/sessions.py usage [--since YYYY-MM-DD] [--exclude SESSION_ID] [--json]
```

- `list`: 対象日に記録のあるセッションを、リポジトリ（worktree なら元リポジトリも）ごとに一覧する
- `digest`: 1 セッションを「ユーザー発言 / Claude の応答 / 使用ツール / エラー」の可読テキストに変換する
- `usage`: Skill ごとの呼び出し回数・使用セッション数・使用リポジトリ数・初回と最終の使用日を集計する（`tidy` が使う）。`<command-name>` タグ付きの起動と `Skill` ツール呼び出しだけを数え、組み込みコマンドとサブエージェント内の呼び出しは除く。実データの開始日を表示し、`--since` がそれより前なら警告する
- `--exclude`: 実行中のセッション自身（`${CLAUDE_SESSION_ID}`）を集計から外す

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
