# skill-kit

Skill 候補から Skill を作り、価値が確認できたものを社内マーケットプレイスへ登録するための手順です。
`worklog` の `/worklog:daily-review` が残した候補を受け取る想定ですが、単体でも使えます。

## 提供するスキル

| スキル | 起動 | 説明 |
|---|---|---|
| `create` | `/skill-kit:create [候補名 または 説明]` | 作成判断チェックリストを通し、個人（`~/.claude/skills/`）またはリポジトリ（`.claude/skills/`）に雛形から SKILL.md を書く |
| `publish` | `/skill-kit:publish <skill のディレクトリ> [マーケットプレイス clone のパス]` | 共有基準を確認し、`plugins/<plugin>/` に複製、`plugin.json` / `marketplace.json` を更新、validate してブランチにコミットする |

どちらも Claude が自動で起動することはありません（`disable-model-invocation: true`）。

## Skill のライフサイクル

```
candidate（~/.agent-worklog/candidates/skills.md）
  → 個人               /skill-kit:create
  → リポジトリ          /skill-kit:create
  → 社内               /skill-kit:publish → push と Pull Request は人が行う
```

作成判断・共有基準・外部 Skill の扱いは `references/skill-lifecycle.md` にまとめています。

## 前提

- `create`: なし
- `publish`: マーケットプレイスリポジトリの clone が手元にあり、作業ツリーがきれいであること。`claude plugin validate` が使えること

## 書く場所

- `create`: 指定した skills ディレクトリと、`~/.agent-worklog/candidates/skills.md` の状態欄
- `publish`: マーケットプレイス clone 内（新しいブランチにコミット）。push はしない

外部通信はしません。
