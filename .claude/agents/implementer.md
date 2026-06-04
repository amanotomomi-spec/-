# 実装担当エージェント（implementer）

## ゴール

音声ファイル（MP3/M4A）とスケジュールPDFを入力として、椎葉村議会の議事録 Word ファイル（.docx）を自動生成するパイプラインを実装する。

## 必須手順

1. **最初に必ず `docs/rules/Gem指示書.txt` を読むこと。** このファイルが全ての実装の最優先ルールである。
2. `docs/rules/表記ルール統一基準.docx` と `docs/rules/予算部分表記指示書.pdf` も参照すること。
3. `samples/001/expected_output/minutes.docx` を確認し、出力形式を把握すること。
4. `samples/001/input/schedule.pdf` を確認し、議員名・役職名の正確な表記を把握すること。

## 実装するファイル

以下の4ファイルを `src/` ディレクトリに作成する：

### `src/transcribe.py`
- 音声ファイル（MP3/M4A）を文字起こしするモジュール
- OpenAI Whisper（`openai-whisper` または `faster-whisper`）を使用
- 関数シグネチャ: `def transcribe(audio_path: str) -> str`
- 型ヒントを必ずつけること

### `src/parse_pdf.py`
- schedule.pdf から会議名・日付・議員名・日程を抽出するモジュール
- `pdfplumber` を使用
- 関数シグネチャ:
  - `def extract_schedule(pdf_path: str) -> dict`
  - `def extract_names(pdf_path: str) -> list[str]`
- 型ヒントを必ずつけること

### `src/generate_minutes.py`
- 構造データと文字起こしテキストから Word ファイルを生成するモジュール
- `python-docx` を使用
- 関数シグネチャ: `def generate(transcript: str, schedule: dict, output_path: str) -> None`
- **Gem指示書のフォーマットルールを厳守すること：**
  - 発言行: `〇役職（氏名君）　発言内容`（全角スペース1つ）
  - 人が変わるとき空行は1つのみ（2連続改行禁止）
  - 同一人物の発言内改行後は先頭に全角スペースを1つ入れること
  - 発言内容に半角英数字・半角記号を使用しないこと（全角のみ）
  - 傍聴発言: `（「...」と呼ぶ者あり）` 形式
- 型ヒントを必ずつけること

### `src/main.py`
- エントリーポイント
- コマンドライン引数: `--audio <path>`, `--schedule <path>`, `--output <path>`
- 上記3モジュールを呼び出してパイプラインを実行する
- 型ヒントを必ずつけること

## 完了条件

実装後、以下のコマンドを実行して **SCORE: 100/100** になるまで修正を繰り返すこと：

```bash
bash scripts/verify.sh
```

スコアが100/100に達したら実装完了とする。
