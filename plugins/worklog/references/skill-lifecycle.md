# Skill のライフサイクル

```
candidate（~/.agent-worklog/candidates/skills.md）
  → 個人（~/.claude/skills/<name>/）
  → リポジトリ（<repo>/.claude/skills/<name>/）
  → 社内（マーケットプレイスの plugins/<plugin>/skills/<name>/）
```

共有範囲が広がるほど、要求されるメタ情報と保守責任が増える。
不要・陳腐化した Skill は削除・更新する。Skill にも保守コストと負債がある。
各段階の見直しは `/worklog:tidy` が使用実績と最終確認日をもとに定期的に提案する。

| 段階 | 誰が動かすか |
|---|---|
| candidate → 個人 / リポジトリ | `/worklog:end`。再検出された候補、または `/worklog:end <候補名>` で明示した候補。手順は `skill-creation.md` |
| 個人 / リポジトリ → 社内 | `/worklog:publish`。push と Pull Request は人が行う |
| 見直し・削除・移動 | `/worklog:tidy`。提案のみ。削除は承認制 |

## Skill 作成判断

候補が見つかっても即座に作らない。初回検出は記録に留め、再検出を待つ。作成前に次を **すべて** 確認する。

1. 既存の公式 Skill（`/help` の一覧）で代用できないか
2. 社内マーケットプレイスに類似 Skill がないか
3. docs で十分ではないか
4. AGENTS.md / CLAUDE.md で十分ではないか
5. script で十分ではないか
6. 本当に再利用する可能性が高いか（再検出の実績は判断材料の一つ。「N 回で必ず Skill 化」のような固定ルールにしない）
7. 対象範囲が明確か

評価軸: 再利用頻度、判断の複雑さ、手順の安定性、毎回の説明コスト、プロジェクト固有性、組織固有性、失敗した場合の影響。

Skill にするのは、AI の判断が必要で、複数ステップからなり、同じ判断方法を繰り返し使い、手順に安定性があるものだけ。
format / build / test / lint のような決定的処理は script にする。

## Skill に含める内容

`templates/SKILL-template.md` を使う。

- Purpose / When to use / When not to use / Workflow / Inputs / Outputs
- Required tools / Required scripts / Validation / Scope / Limitations
- owner / version / 最終確認日 / maintenance policy

frontmatter:

- `description`: 何をするかと、いつ使うかを先頭に。Claude はこの文で自動起動を判断する
- `disable-model-invocation: true`: 手動でしか起動させたくない場合（副作用のある手順は原則 true）
- `allowed-tools`: 事前許可は最小限。書き込み系は入れない

## 社内共有の基準

マーケットプレイスへ登録する Skill は、次を SKILL.md または プラグインの README に明記する。

| 項目 | 内容 |
|---|---|
| owner | 保守責任者 |
| version | 更新配信のトリガー。変更のたびに上げる |
| scope | 対象リポジトリ・対象作業 |
| dependencies | 必要なツール・スクリプト・環境 |
| expected usage | 想定する使い方 |
| when not to use | 使ってはいけない状況 |
| maintenance policy | 誰が・いつ見直すか |
| 最終確認日 | 最後に動作と内容を確認した日 |

加えて、共有前に次を確認する。

- リポジトリ固有の絶対パス、個人名、トークン等が本文に残っていないこと
- hooks / MCP / 外部通信を含む場合は、その内容がレビューで監査できる状態であること
- 同梱スクリプトは読み取り専用か、書き込む範囲が明記されていること

## 外部 Skill / Plugin の扱い

- 第三者の Skill / Plugin は無条件にインストールしない。まず参考実装・設計事例として評価する
- Anthropic 公式のものは社内ルール上問題なければ利用候補
- 社内固有の重要ワークフローは社内実装・社内管理
- 設計を参考にした場合は README の References に記録する。コード・文章の転用はライセンスと社内 OSS ルールを確認する
- 直接利用する場合は、提供元・ライセンス・hooks・実行される shell command・MCP・外部通信・データ送信先・ファイルアクセス・更新方式・version 固定可否・maintenance 状況を確認する
