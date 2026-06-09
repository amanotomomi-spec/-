# new-meeting

新しい会議用の config.yaml を作成し、ディレクトリ構造を準備します。

## 手順

### ステップ 1: 会議情報の収集

ユーザーに以下を確認する:

- **会議番号 / 会議名**: 例「003」「令和８年第３回臨時会」
- **開催日**: 例「令和８年６月１０日（火曜日）」
- **開会時刻**: 例「午前１０時００分開会」

未指定の場合は既存の `samples/` ディレクトリを確認して次の番号を提案する:

```bash
ls samples/
```

### ステップ 2: ディレクトリの作成

```bash
mkdir -p samples/NNN/input
mkdir -p samples/NNN/output
```

### ステップ 3: テンプレートのコピー

`samples/002/input/config.yaml` をテンプレートとして新しいディレクトリにコピーする:

```bash
cp samples/002/input/config.yaml samples/NNN/input/config.yaml
```

### ステップ 4: メタデータの更新

コピーした config.yaml の以下のフィールドをユーザーから収集した情報で更新する:

```yaml
meeting:
  title: "令和８年第N回（臨時会）椎葉村議会会議録（第１日）"
  date: "令和８年M月D日（X曜日）"
  open_time: "午前HH時MM分開会"
```

`agenda_items` は会議の種類に応じてユーザーに確認するか、後で編集してもらうよう案内する。

### ステップ 5: 議員・出席者の確認

作成した config.yaml の `speakers` セクションを表示し、以下を確認する:

「前回（002）から人事異動はありましたか？役職・氏名に変更がある場合はお知らせください。」

変更がある場合は `speakers` セクションと `members` セクションを更新する。

### ステップ 6: 完成した config.yaml の表示

最終的な config.yaml の内容を表示し、以下を案内する:
- 「Notta テキストを `samples/NNN/input/notta.txt` に配置したら `/generate-minutes` で議事録を生成できます。」
