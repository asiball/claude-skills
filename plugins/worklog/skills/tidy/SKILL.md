---
name: tidy
description: 蓄積した Skill 候補、個人・リポジトリの Skill、社内公開済み Skill を棚卸しする。使用実績と最終確認日を集計し、放置された候補の整理、未使用 Skill の削除や昇格、最終確認日の更新を提案する。週 1 か月 1 の頻度で手動で実行する。
argument-hint: "[マーケットプレイス clone のパス]"
disable-model-invocation: true
allowed-tools:
  - Read
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
| 個人・リポジトリの Skill | 90 日以上未使用 | 削除。迷う場合は次回まで保留 |
| 個人の Skill | 直近 90 日で 5 回以上、かつ複数リポジトリで使用 | リポジトリまたは社内への昇格を検討 |
| 社内公開済み Skill | 最終確認日から 180 日以上 | owner に見直しを依頼 |

## 手順

### 1. 使用実績を集計する

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sessions.py usage --since <90 日前の YYYY-MM-DD>
```

Skill ごとの呼び出し回数・使用セッション数・使用リポジトリ数・初回と最終の使用日が出る。
この棚卸しを実行している現在のセッション自身の `worklog:tidy` は除いて考える。

### 2. 候補を点検する

`~/.agent-worklog/candidates/{knowledge,automation,skills}.md` を読む。

- `candidate` のまま初回検出から 60 日以上経過し、再検出がないもの → `rejected` を提案
- `applied` だが「作成先」のパスが存在しないもの → 実態を確認し、状態の修正を提案
- 同じ内容のエントリが複数あるもの → 統合を提案

エントリは削除しない。状態と理由を追記して履歴として残す。`end` が再検出時に照合するため。

### 3. 個人・リポジトリの Skill を点検する

```
ls ~/.claude/skills/
ls <現在のリポジトリ>/.claude/skills/
```

各 SKILL.md を読み、手順 1 の使用実績と照合する。

- 90 日以上未使用 → 削除を提案。判断がつかなければ「次回まで保留」として記録する
- 個人の Skill で使用が多く、複数リポジトリにわたる → リポジトリへの移動、または `/worklog:publish` を案内
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
ls ~/.agent-worklog/daily | wc -l
```

件数とサイズを報告する。Daily Review は履歴なので既定では削除しない。ユーザーが望めば、1 年以上前の分の削除を提案してよい。

### 6. 提案する

一覧表で示す: 対象 / 現状（使用回数・最終使用日・最終確認日） / 提案 / 理由。
提案ごとに個別に承認をとる。

### 7. 実行する

承認されたものだけ実行する。

- 候補: 状態と理由を追記する
- 個人 Skill: 削除、内容の更新、または最終確認日の更新
- リポジトリ Skill: 作業ツリーを編集する。コミットは人が行う
- 社内 Skill: clone の作業ツリーを編集し、`version` を上げる。push と Pull Request は人が行う。owner が別の人なら依頼文を用意する

### 8. 記録して報告する

`~/.agent-worklog/tidy/<今日の日付>.md` に、提案の一覧と各項目の決定（実行 / 見送り / 保留）を書く。次回の棚卸しで「保留」の再評価に使う。

最後に、実行したもの・見送ったもの・保留にしたもの・人に依頼するものを短く一覧にする。
