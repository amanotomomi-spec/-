# learn-corrections

生成済みの議事録と修正済み議事録を比較し、差分をルールとして永続的に保存します。

## 手順

### ステップ 1: ファイルパスの確認

ユーザーに以下を確認する:

- **生成済み（修正前）.docx パス**: 例 `samples/003/output/minutes.docx`
- **修正済み .docx パス**: 例 `samples/003/output/minutes_corrected.docx`
- **対応する config.yaml パス**: 例 `samples/003/input/config.yaml`（テキスト誤変換の保存先）

### ステップ 2: 両ファイルの段落抽出と比較

python-docx を使って差分を抽出する:

```python
from docx import Document

def extract_paragraphs(path):
    doc = Document(path)
    return [p.text for p in doc.paragraphs]

original = extract_paragraphs("<generated_docx>")
corrected = extract_paragraphs("<corrected_docx>")

# 差分の検出
import difflib
diff = list(difflib.ndiff(original, corrected))
changes = [(i, line) for i, line in enumerate(diff) if line.startswith("- ") or line.startswith("+ ")]
```

### ステップ 3: 差分の分類

差分を以下の3カテゴリに分類する:

#### a. テキスト誤変換（config.yaml の `extra_corrections` に追記）
- 固有名詞の誤認識
- 数字・金額の誤変換
- 専門用語の誤変換

例:
```yaml
extra_corrections:
  - ["しいばそん", "椎葉村"]
  - ["ひじりかわ", "聖川"]
```

#### b. 発言者誤検出（`src/parse_notta.py` の `CORRECTIONS` リストを更新）
- 発言者の割り当てミス
- 発言境界の誤検出

変更案を提示し、ユーザーに確認を取る。

#### c. フォーマット差異（`CLAUDE.md` の「学習済みルール」セクションに追記）
- 段落の結合・分割パターン
- 特殊な表記の処理方法

### ステップ 4: 変更案の提示

分類した変更内容をすべて表示し、ユーザーに確認を取る:

「以下の変更を適用します。よろしいですか？

**config.yaml への追記（テキスト誤変換）:**
（変更内容を表示）

**src/parse_notta.py への変更（発言者誤検出）:**
（変更内容を表示）

**CLAUDE.md への追記（フォーマットルール）:**
（変更内容を表示）」

### ステップ 5: 変更の適用

ユーザーの確認後、以下を順番に実行する:

1. config.yaml の `extra_corrections` を更新する
2. `src/parse_notta.py` の CORRECTIONS リストを更新する
3. `CLAUDE.md` に「学習済みルール」セクションが存在しない場合は追加、存在する場合は追記する

### ステップ 6: コミット

```bash
git add samples/NNN/input/config.yaml src/parse_notta.py CLAUDE.md
git commit -m "学習: <会議名>の修正内容を反映"
git push
```

「学習内容を保存しました。次回の議事録生成から反映されます。」と報告する。
