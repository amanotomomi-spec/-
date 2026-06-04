# テスト担当エージェント（tester）

## ゴール

`tests/` ディレクトリのテストを実行し、カバレッジを測定して、不足しているテストケースを追加する。

## 必須手順

1. `tests/` ディレクトリの全テストファイルを読む。
2. 以下のコマンドでテストとカバレッジを実行する：

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

3. カバレッジが低い箇所（80%未満）にテストケースを追加する。
4. `tests/test_format.py` と `tests/test_proper_nouns.py` の不足テストケースを補完する。

## テスト追加の観点

### `tests/test_format.py` の追加テストケース候補

- 発言行の全角スペースが半角スペースになっているケース
- 人が変わるとき空行が2つ以上あるケース
- 発言内容が空のケース
- `〇` と `○` の両方の先頭記号を正しく処理するケース
- 傍聴発言の括弧が半角のケース

### `tests/test_proper_nouns.py` の追加テストケース候補

- PDF に存在する氏名がdocxで別表記になっているケース
- 番号付き議員名（例: `２番　藏座　二九生`）の正しい氏名抽出
- 氏名リストが空のときのエラーハンドリング

### `src/` モジュールのテスト

- `src/parse_pdf.py` の `extract_schedule` と `extract_names` の単体テスト
- `src/generate_minutes.py` のフォーマット出力テスト
- `src/transcribe.py` のモックテスト（実際のWhisper不要）

## 完了条件

- `pytest tests/ -v` が全て PASS すること
- カバレッジが `src/` の主要関数で 80% 以上であること
