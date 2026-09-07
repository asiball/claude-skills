---
name: <skill-name>
description: <何をするか。いつ使うかを先頭に書く。Claude はこの文で自動起動を判断する>
argument-hint: "[<引数の例>]"
# 手動でしか起動させない場合は true
disable-model-invocation: false
# 事前に許可する読み取り系ツール。書き込み系は入れない。不要なら削除する
allowed-tools:
  - Read
---

# <Skill 名>

## Purpose

この Skill が解決すること。1〜3 行。

## When to use

- 使うべき状況

## When not to use

- 使ってはいけない状況
- script / docs / AGENTS.md で済む場合はそちらへ

## Workflow

1. 手順
2. 手順
3. 手順

## Inputs

- `$ARGUMENTS`: 何を受け取るか
- 参照するファイル・情報

## Outputs

- 生成・更新するもの

## Required tools

- 使うツール（Read / Bash(git ...) など）

## Required scripts

- 同梱スクリプトがあればパスと用途

## Validation

- 結果が正しいことをどう確認するか

## Scope

- 個人 / リポジトリ / 社内 のどれか
- 対象リポジトリ・対象ファイル

## Limitations

- できないこと、前提条件

---

- owner: <名前>
- version: 0.1.0
- 最終確認日: <YYYY-MM-DD>
- maintenance policy: <誰が・どのタイミングで見直すか>
