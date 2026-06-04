# ドキュメント担当エージェント（documenter）

## ゴール

`src/` ディレクトリのコードから docstring を確認し、`docs/api.md` にAPIリファレンスと使い方ガイドを記載する。

## 必須手順

1. `src/` ディレクトリの全 `.py` ファイルを読む。
2. 各関数・モジュールの docstring を確認する。
3. `docs/api.md` を作成（または更新）する。

## `docs/api.md` の構成

以下の内容を含めること：

```markdown
# 椎葉村議会 議事録自動生成システム APIリファレンス

## インストール

## クイックスタート

## モジュール一覧

### src/transcribe.py
- 関数シグネチャ
- 引数の説明
- 戻り値の説明
- 使用例

### src/parse_pdf.py
- 関数シグネチャ
- 引数の説明
- 戻り値の説明
- 使用例

### src/generate_minutes.py
- 関数シグネチャ
- 引数の説明
- 戻り値の説明
- 使用例

### src/main.py
- コマンドライン引数の説明
- 使用例

## サンプルコマンド

## トラブルシューティング
```

## サンプルコマンドの例

以下のようなコマンド例を必ず含めること：

```bash
# 基本的な使い方
python src/main.py --audio samples/001/input/audio.mp3 --schedule samples/001/input/schedule.pdf --output output/minutes.docx

# テスト実行
pytest tests/ -v

# 検証スクリプト実行
bash scripts/verify.sh

# 型チェック
mypy src/
```

## 完了条件

- `docs/api.md` が作成されていること
- 全ての公開関数がドキュメント化されていること
- サンプルコマンドが動作可能であること
