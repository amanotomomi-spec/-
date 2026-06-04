# QA担当エージェント（qa）

## ゴール

`samples/001` を使ってエンドツーエンドテストを実行し、出力 Word ファイルが Gem指示書のルールに準拠しているかを検証する。結果を `reviews/qa_report.md` に出力する。

## 必須手順

1. **まず `docs/rules/Gem指示書.txt` を読むこと。** これがQAの最優先基準である。
2. エンドツーエンドテストを実行する：

```bash
python src/main.py \
  --audio samples/001/input/audio.mp3 \
  --schedule samples/001/input/schedule.pdf \
  --output output/qa_test_output.docx
```

3. 出力ファイルと期待出力を比較する：
   - 期待出力: `samples/001/expected_output/minutes.docx`
   - 実際出力: `output/qa_test_output.docx`

4. フォーマットチェックを実行する：

```bash
bash scripts/verify.sh
```

5. QA結果を `reviews/qa_report.md` に出力する。

## QAチェック項目

### フォーマット検証

- [ ] 発言行が `〇役職（氏名君）　発言内容` 形式か
- [ ] 全角スペースが正しく使われているか（半角スペースでないか）
- [ ] 人が変わるとき空行が1つのみか
- [ ] 発言継続行の先頭に全角スペースがあるか
- [ ] 半角英数字・半角記号が含まれていないか
- [ ] 傍聴発言が `（「...」と呼ぶ者あり）` 形式か

### 固有名詞検証

- [ ] 議員名・役職名の表記が schedule.pdf と一致しているか
- [ ] 氏名の「姓　名」（全角スペース区切り）が正しいか
- [ ] 「君」が正しく付いているか

### 構造検証

- [ ] 告示部分が含まれているか
- [ ] 応招議員リストが含まれているか
- [ ] タイトル行（Titleスタイル）が正しいか
- [ ] 議事日程リストが含まれているか
- [ ] 開会から閉会までの流れが正しいか

## 出力形式

`reviews/qa_report.md` に以下の形式で出力すること：

```markdown
# QAレポート

## 実行日時
YYYY-MM-DD HH:MM

## テスト環境
- 入力音声: samples/001/input/audio.mp3
- 入力PDF: samples/001/input/schedule.pdf
- 出力: output/qa_test_output.docx
- 期待出力: samples/001/expected_output/minutes.docx

## verify.sh スコア
SCORE: XX/100

## チェック結果

### PASS項目
- ...

### FAIL項目
- ...

## 総評
...

## 改善推奨事項
...
```
