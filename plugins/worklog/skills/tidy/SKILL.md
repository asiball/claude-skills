---
name: tidy
description: 蓄積した Skill 候補、個人・リポジトリの Skill、社内公開済み Skill を棚卸しする。使用実績と最終確認日を集計し、放置された候補の整理、未使用 Skill の削除や昇格、最終確認日の更新を提案する。週 1 か月 1 の頻度で手動で実行する。
argument-hint: "[マーケットプレイス clone のパス]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sessions.py *)
  - Bash(ls *)
  - Bash(du *)
  - Bash(git status *)
  - Bash(git log *)
---

# 棚卸し

Skill とその候補にも保守コストがある。増えたものを定期的に見直し、使われていないものを手放す。

## 原則

- 削除・変更は提案し、承認されたものだけ実行する。自動では消さない
- 「変更なし」は正常な結果
- 判定材料はスクリプトの集計と実ファイルから取る。記憶や印象で判断しない
- リポジトリやマーケットプレイス clone の作業ツリーは、承認された場合にのみ編集する。コミット・push・Pull Request は人が行う
- 外部通信をしない

## 既定のしきい値

ユーザーの指示があれば変えてよい。

| 対象 | 条件 | 提案 |
|---|---|---|
| 候補（`candidate`） | 初回検出から 60 日以上経過し、再検出がない | `rejected`（理由: 再発なし） |
| 個人の Skill | 作成日（または最終確認日）から 90 日以上経過し、その間の使用が 0 回 | 削除。迷う場合は次回まで保留 |
| リポジトリの Skill | 同上 | 削除の**検討**を提案。自分の実績だけでは他の作業者の使用が見えないため、削除の判断は人が行う |
| 個人の Skill | 直近 90 日で 5 回以上、かつ 1 つのリポジトリでのみ使用 | そのリポジトリの `.claude/skills/` への移動を検討 |
| 個人の Skill | 直近 90 日で 5 回以上、かつ複数リポジトリで使用 | 社内共有（`/worklog:publish`）を検討 |
| 社内公開済み Skill | 最終確認日から 180 日以上 | owner に見直しを依頼 |

使用実績は手元の transcript からしか取れない。transcript は Claude Code の `cleanupPeriodDays`（既定 30 日）で削除されるため、**集計の実データ範囲がしきい値より短い場合、「未使用」を理由にした削除提案はしない**。その場合は範囲を報告し、しきい値を範囲内に縮めるか、次回まで保留にする。

## 手順

### 1. 使用実績を集計する

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sessions.py usage --since <90 日前の YYYY-MM-DD> --exclude ${CLAUDE_SESSION_ID}
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sessions.py usage --since <90 日前の YYYY-MM-DD> --exclude ${CLAUDE_SESSION_ID} --json
```

Skill ごとの呼び出し回数・使用セッション数・使用リポジトリ数・初回と最終の使用日が出る。
先頭の `oldest record` が実データの開始日。`WARNING` が出ていれば、その範囲より前の使用は見えていない。
`--json` の `repos` に出たリポジトリが、手順 3 で `.claude/skills/` を見に行く対象になる。

### 2. 候補を点検する

`~/.agent-worklog/candidates/{knowledge,automation,skills}.md` を読む。

- `candidate` のまま初回検出から 60 日以上経過し、再検出がないもの → `rejected` を提案
- `applied` だが「作成先」のパスが存在しないもの → 実態を確認し、状態の修正を提案
- 同じ内容のエントリが複数あるもの → 統合を提案

エントリは削除しない。状態と理由を追記して履歴として残す。`end` が再検出時に照合するため。

### 3. 個人・リポジトリの Skill を点検する

```
ls ~/.claude/skills/
ls <リポジトリ>/.claude/skills/      # 現在のリポジトリと、手順 1 の repos に出た各リポジトリ
```

各 SKILL.md を読み、手順 1 の使用実績と照合する。作成日は SKILL.md の `version` / 最終確認日、または `candidates/skills.md` の「作成日」から取る。

- 作成から 90 日以上経過し、実データ範囲内で未使用 → 個人なら削除を提案。リポジトリなら削除の検討を提案（判断は人）。判断がつかなければ「次回まで保留」として記録する
- 個人の Skill で使用が多い → 1 リポジトリのみなら移動、複数リポジトリなら `/worklog:publish` を案内
- 参照しているファイル・コマンド・手順が現状と合っていない → 更新を提案
- owner / version / 最終確認日 / maintenance policy がない → 追記を提案
- 内容と動作に問題がないと確認できたもの → 最終確認日を今日に更新する提案

### 4. 社内公開済み Skill を点検する

`$ARGUMENTS` にマーケットプレイス clone のパスがある場合のみ。

- 各プラグインの `plugin.json` と `marketplace.json` で `version` と `description` が一致しているか
- 各プラグインの README または SKILL.md に owner / version / 最終確認日 / maintenance policy があるか
- 最終確認日から 180 日以上経過 → owner への見直し依頼を提案
- `marketplace.json` の `renames` は移行履歴なので消さない

自分の使用実績（`/<plugin>:<name>`）は参考として添えるが、社内 Skill の削除は 1 人の使用実績だけで判断しない。

### 5. 蓄積ファイルの量を確認する

```
du -sh ~/.agent-worklog/daily ~/.agent-worklog/candidates
ls ~/.agent-worklog/daily
```

件数とサイズを報告する。Daily Review は履歴なので既定では削除しない。ユーザーが望めば、1 年以上前の分の削除を提案してよい。

### 6. 提案する

一覧表で示す: 対象 / 現状（使用回数・最終使用日・最終確認日） / 提案 / 理由。
提案ごとに個別に承認をとる。

### 7. 実行する

承認されたものだけ実行する。

- 候補: 状態と理由を追記する
- 個人 Skill: 削除、内容の更新、または最終確認日の更新
- 個人 → リポジトリへの移動: `~/.claude/skills/<name>/` を `<repo>/.claude/skills/<name>/` にコピーし、動作を確認してから元を削除する。`candidates/skills.md` の「作成先」を更新する。コミットは人が行う
- リポジトリ Skill: 作業ツリーを編集する。コミットは人が行う
- 社内 Skill: clone の作業ツリーを編集し、`version` を上げる。push と Pull Request は人が行う。owner が別の人なら依頼文を用意する

### 8. 記録して報告する

`~/.agent-worklog/tidy/<今日の日付>.md` に、提案の一覧と各項目の決定（実行 / 見送り / 保留）を書く。次回の棚卸しで「保留」の再評価に使う。

最後に、実行したもの・見送ったもの・保留にしたもの・人に依頼するものを短く一覧にする。
