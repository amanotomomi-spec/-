# generate-minutes

議事録（Word ファイル）を Notta テキストと config.yaml から生成します。

## 手順

### ステップ 1: 入力ファイルの確認

ユーザーに以下を確認してください（未指定の場合はスマートデフォルトを提案する）:

- **Notta TXT パス**: 例 `samples/NNN/input/notta.txt`
- **config.yaml パス**: 例 `samples/NNN/input/config.yaml`
- **出力 docx パス**: 例 `samples/NNN/output/minutes.docx`

ユーザーが会議番号（例: `003`）だけを言った場合は以下をデフォルトとして使用する:
- `samples/003/input/notta.txt`
- `samples/003/input/config.yaml`
- `samples/003/output/minutes.docx`

### ステップ 2: 出力ディレクトリの作成

```bash
mkdir -p <output_dir>
```

### ステップ 3: 議事録生成コマンドの実行

```bash
python3 src/main_v2.py --notta <notta_txt> --config <config_yaml> --output <output_docx>
```

実行ログを表示し、エラーがあれば内容を確認して対処する。

### ステップ 4: 結果の確認

生成後、python-docx で以下を確認して報告する:

```python
from docx import Document
doc = Document("<output_docx>")
paras = [p.text for p in doc.paragraphs if p.text.strip()]
print(f"段落数: {len(paras)}")
warnings = [p.text for p in doc.paragraphs if "【要確認】" in p.text]
print(f"【要確認】箇所: {len(warnings)}件")
for w in warnings:
    print(f"  - {w[:80]}")
```

報告内容:
- 出力ファイルのパス
- 総段落数
- 【要確認】マークの件数と内容

### ステップ 5: ファイルをユーザーに送信

SendUserFile ツールを使って生成した .docx ファイルをユーザーに送信する。

### ステップ 6: フォローアップ

以下を尋ねる:
- 「修正が必要な箇所はありましたか？修正済みファイルがあれば `/learn-corrections` で学習できます。」
- 「フォーマットの自動チェックを行いますか？ `/verify-minutes` で確認できます。」
