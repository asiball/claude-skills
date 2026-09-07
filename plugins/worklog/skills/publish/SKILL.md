---
name: publish
description: 個人またはリポジトリの Skill を社内マーケットプレイスのプラグインとして登録する。plugin.json / marketplace.json を更新し、validate してブランチにコミットする。push と Pull Request は人が行う。
argument-hint: "<skill のディレクトリ> [マーケットプレイス clone のパス]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash(claude plugin validate *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git log *)
  - Bash(git diff *)
---

# Skill を社内マーケットプレイスへ登録する

個人・リポジトリで価値が確認できた Skill を、マーケットプレイスの `plugins/` に複製して登録し、レビュー用のコミットを作る。
push と Pull Request は人が行う。

## 手順

### 1. 入力を確認する

- Skill ディレクトリ: `$ARGUMENTS` の 1 つ目。`SKILL.md` があること
- マーケットプレイス clone: `$ARGUMENTS` の 2 つ目。なければユーザーに聞く。`.claude-plugin/marketplace.json` があること

### 2. clone の状態を確認する

```
git -C <clone> status --short
git -C <clone> branch --show-current
```

未コミットの変更があれば中断する。既定ブランチ（main）でなければ、切り替えてよいかユーザーに確認する。
最新化（`git pull`）は人が行う前提だが、古い可能性があれば注意を伝える。

### 3. 共有基準を確認する

`${CLAUDE_PLUGIN_ROOT}/references/skill-lifecycle.md` の「社内共有の基準」に照らして SKILL.md を読む。

- owner / version / scope / dependencies / expected usage / when not to use / maintenance policy / 最終確認日 が揃っているか
- `description` が「何をするか・いつ使うか」を表しているか
- 絶対パス、個人名、トークン、社外に出せない情報が本文・scripts に残っていないか
- hooks / MCP / 外部通信 / 書き込み処理があれば、その範囲が README で説明できるか

不足があれば、ユーザーと相談して埋めてから進む。

### 4. 配置先を決める

ユーザーに確認する。

- 新規プラグイン `plugins/<plugin>/`: 独立した関心事のとき。単一 Skill なら plugin 名 = skill 名でよい
- 既存プラグインへ追加 `plugins/<plugin>/skills/<name>/`: 既存の関心事に属するとき

呼び出しは `/<plugin>:<name>` になる。声に出して読める組み合わせにする。

### 5. 複製・登録する

新規プラグインの場合:

1. `plugins/<plugin>/skills/<name>/` に SKILL.md と同梱物（references / templates / scripts）をコピーする。同梱物を複数の Skill で共有するならプラグインルート直下（`plugins/<plugin>/references/` など）に置く
2. `plugins/<plugin>/.claude-plugin/plugin.json` を作る: `name` / `description` / `version: 0.1.0` / `author`
3. `plugins/<plugin>/README.md` を作る: 提供するスキル、使い方、前提、読む・書く場所、owner、maintenance policy
4. `.claude-plugin/marketplace.json` の `plugins` に `{ name, source: "./plugins/<plugin>", description, version }` を追記する
5. ルート `README.md` のプラグイン一覧に行を追加する

既存プラグインへ追加する場合:

1. `plugins/<plugin>/skills/<name>/` にコピーする
2. `plugin.json` と `marketplace.json` の `version` を上げる（上げないと利用者に配信されない）
3. プラグインの README にスキルを追記する

どちらの場合も、SKILL.md 内で同梱物を指す相対パス（`references/...` `scripts/...` など）は `${CLAUDE_PLUGIN_ROOT}/...` に書き換える。個人・リポジトリの Skill では相対パスで動いていても、プラグインでは `${CLAUDE_PLUGIN_ROOT}` 基準になる。

### 6. 検証する

```
claude plugin validate <clone>/plugins/<plugin> --strict
claude plugin validate <clone> --strict
```

失敗したら直してから進む。

### 7. コミットする

ブランチを切ってコミットする。push はしない。

```
git -C <clone> switch -c add/<plugin>        # 既存プラグインへの追加なら update/<plugin>
git -C <clone> add -A
git -C <clone> commit -m "add <plugin>: <name>"
```

### 8. 案内する

次をユーザーに示す:

- push コマンド: `git -C <clone> push -u origin add/<plugin>`
- GitBucket で Pull Request を作ること
- レビュアーに伝える確認観点: hooks / MCP / 外部通信の有無、scripts の内容と書き込み範囲、共有基準の充足
- マージ後、利用者は `/plugin marketplace update <marketplace 名>` で取り込めること
