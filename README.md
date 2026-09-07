# claude-skills

社内向け Claude Code プラグインのマーケットプレイスです。
各プラグインの詳細は `plugins/<name>/README.md` を参照してください。

## プラグイン一覧

| プラグイン | スキル | 概要 |
|---|---|---|
| [worklog](plugins/worklog/README.md) | `/worklog:end` `/worklog:tidy` `/worklog:publish` | 1日の作業を振り返って再利用候補を分類・Skill 化し、Skill を定期的に棚卸しし、価値が確認できた Skill を社内へ登録する |

## 導入

### 1. マーケットプレイスを登録する

Claude Code 内で実行します。

```
/plugin marketplace add http://<gitbucket-host>/git/<owner>/claude-skills.git
```

`http://` の URL が受け付けられない場合は、リポジトリをクローンしてローカルパスで登録してください。

```
git clone http://<gitbucket-host>/git/<owner>/claude-skills.git ~/claude-skills
/plugin marketplace add ~/claude-skills
```

プロジェクト単位で自動登録したい場合は、そのプロジェクトの `.claude/settings.json` に書きます（フォルダを信頼した人全員に適用されます）。

```json
{
  "extraKnownMarketplaces": {
    "claude-skills": {
      "source": { "source": "url", "url": "http://<gitbucket-host>/git/<owner>/claude-skills.git" }
    }
  },
  "enabledPlugins": {
    "worklog@claude-skills": true
  }
}
```

### 2. プラグインをインストールする

```
/plugin install worklog@claude-skills
```

インストール後、`/worklog:` まで入力すると補完でスキルが並びます。

### 3. 更新を取り込む

```
/plugin marketplace update claude-skills
```

更新はプラグインの `version` が上がったときにだけ配信されます。

| 変更の種類 | 利用者側に必要なこと |
|---|---|
| プラグイン内のスキル追加・改名・削除 | `version` が上がっていれば update で反映。再インストール不要 |
| プラグインの改名・統合・削除 | `marketplace.json` の `renames` に旧名を書く（統合先の名前、削除なら `null`）。利用者は次回起動時に自動移行される（v2.1.193 以降）。`renames` は履歴として残し続ける |

## 用語

| 用語 | 実体 | 役割 |
|---|---|---|
| スキル | `skills/<name>/SKILL.md` | Claude への手順書。`/plugin:name` で実行する単位 |
| プラグイン | `plugins/<name>/` | スキルをまとめた配布単位。スキル名の前に `plugin:` が付く |
| マーケットプレイス | このリポジトリ | プラグインのカタログ。`.claude-plugin/marketplace.json` が一覧 |

マーケットプレイス名（`marketplace.json` の `name`）は `/plugin install worklog@<name>` の `@` 以降に出ます。社内へコピーする際に社名・部署名入りに変えて構いません（誰かが install する前なら影響なし）。

## プラグインを追加・更新する

1. ブランチを切り、`plugins/<name>/` を作成する（構成は `plugins/worklog/` を参照）
2. `.claude-plugin/marketplace.json` の `plugins` に追記する
3. 手元で検証する
   ```
   claude plugin validate ./plugins/<name>
   claude --plugin-dir ./plugins/<name>
   ```
   （既存の Skill を登録する場合は 1〜3 を `/worklog:publish` が行います）
4. GitBucket で Pull Request を作成し、レビューを受ける
5. マージ後、利用者は `/plugin marketplace update claude-skills` で取り込む

既存プラグインを変更した場合は `plugin.json` と `marketplace.json` の `version` を上げてください。

## Skill の昇格

Skill はいきなり社内共有せず、次の順で範囲を広げます。

```
候補（~/.agent-worklog/candidates/skills.md）   ← /worklog:end が記録
  → 個人（~/.claude/skills/<name>/）             ← /worklog:end が再検出時に作成（置き場所は作成時に選ぶ）
  → リポジトリ（<repo>/.claude/skills/<name>/）   ← 同上
  → 社内（このリポジトリへ PR）                    ← /worklog:publish がコミットまで行い、push と PR は人が行う
  各段階の見直し・削除                             ← /worklog:tidy が定期的に提案
```

社内共有する Skill には、owner・version・scope・when not to use・maintenance policy・最終確認日を README または SKILL.md に明記してください。
陳腐化した Skill は削除・更新の対象とし、Skill にも保守コストがあるものとして扱います。
