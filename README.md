# claude-skills

社内向け Claude Code プラグインのマーケットプレイスです。
各プラグインの詳細は `plugins/<name>/README.md` を参照してください。

## プラグイン一覧

| プラグイン | 提供するスキル | 概要 |
|---|---|---|
| [worklog](plugins/worklog/README.md) | `/worklog:daily-review` | 1日の作業を振り返り、再利用候補を docs / README / AGENTS.md / script / Skill に分類する |
| [skill-kit](plugins/skill-kit/README.md) | `/skill-kit:create` `/skill-kit:publish` | Skill 候補から Skill を作成し、価値が確認できたものをこのマーケットプレイスへ登録する |

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

インストール後に `/help` の Custom commands タブにスキルが表示されます。
更新は `/plugin` の管理画面、または `/plugin marketplace update claude-skills` で取り込みます。
更新はプラグインの `version` が上がったときにだけ配信されます。

## 用語

| 用語 | 実体 | 役割 |
|---|---|---|
| スキル | `skills/<name>/SKILL.md` | Claude への手順書。`/name` で実行する単位 |
| プラグイン | `plugins/<name>/` | スキルをまとめた配布単位。スキル名の前に `plugin:` が付く |
| マーケットプレイス | このリポジトリ | プラグインのカタログ。`.claude-plugin/marketplace.json` が一覧 |

## プラグインを追加・更新する

1. ブランチを切り、`plugins/<name>/` を作成する（構成は `plugins/worklog/` を参照）
2. `.claude-plugin/marketplace.json` の `plugins` に追記する
3. 手元で検証する
   ```
   claude plugin validate ./plugins/<name>
   claude --plugin-dir ./plugins/<name>
   ```
   （既存の Skill を登録する場合は 1〜3 を `/skill-kit:publish` が行います）
4. GitBucket で Pull Request を作成し、レビューを受ける
5. マージ後、利用者は `/plugin marketplace update claude-skills` で取り込む

既存プラグインを変更した場合は `plugin.json` と `marketplace.json` の `version` を上げてください。

## Skill の昇格

Skill はいきなり社内共有せず、次の順で範囲を広げます。

```
候補（~/.agent-worklog/candidates/skills.md）   ← /worklog:daily-review が記録
  → 個人（~/.claude/skills/<name>/）             ← /skill-kit:create
  → リポジトリ（<repo>/.claude/skills/<name>/）   ← /skill-kit:create
  → 社内（このリポジトリへ PR）                    ← /skill-kit:publish がコミットまで行い、push と PR は人が行う
```

社内共有する Skill には、owner・version・scope・when not to use・maintenance policy・最終確認日を README または SKILL.md に明記してください。
陳腐化した Skill は削除・更新の対象とし、Skill にも保守コストがあるものとして扱います。
