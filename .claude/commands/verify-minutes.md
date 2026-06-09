# verify-minutes

生成した議事録 Word ファイルを Gem指示書のフォーマットルールに従って検証します。

## 手順

### ステップ 1: ファイルパスの確認

ユーザーに確認する:
- **検証する .docx パス**: 例 `samples/003/output/minutes.docx`

### ステップ 2: フォーマットチェックの実行

python-docx を使って以下を一括チェックする:

```python
from docx import Document
import re

doc = Document("<docx_path>")
violations = []

for i, para in enumerate(doc.paragraphs):
    text = para.text
    if not text.strip():
        continue

    # チェック 1: 発言行フォーマット（〇役職（氏名君）　発言内容）
    if text.startswith("〇") or text.startswith("○"):
        # 全角スペースが役職名の後にあるか
        if not re.search(r'[）]　', text):
            violations.append(f"[段落{i+1}] 発言行の全角スペースなし: {text[:50]}")

    # チェック 2: 発言内容に半角文字が混入していないか
    if text.startswith("〇") or text.startswith("○"):
        # 括弧内の氏名部分を除いた発言内容をチェック
        content_match = re.search(r'[）]　(.+)', text)
        if content_match:
            content = content_match.group(1)
            half_width = re.findall(r'[!-~]', content)
            if half_width:
                violations.append(f"[段落{i+1}] 発言内容に半角文字: {''.join(half_width[:10])} ... 「{text[:50]}」")

    # チェック 3: 発言者間に空行がないか（space_after = 0 のはずが空テキストの段落がある）
    if not text.strip() and i > 0:
        prev_text = doc.paragraphs[i-1].text.strip() if i > 0 else ""
        next_text = doc.paragraphs[i+1].text.strip() if i+1 < len(doc.paragraphs) else ""
        if (prev_text.startswith("〇") or prev_text.startswith("○")) and \
           (next_text.startswith("〇") or next_text.startswith("○")):
            violations.append(f"[段落{i+1}] 発言者間に空行あり（段落{i}と段落{i+2}の間）")

    # チェック 4: 傍聴行（（「〜」と呼ぶ者あり））の形式チェック
    if "と呼ぶ者あり" in text:
        if not re.match(r'^（「.+」と呼ぶ者あり）$', text):
            violations.append(f"[段落{i+1}] 傍聴行フォーマット不正: {text}")

    # チェック 5: 【要確認】マークが残っていないか
    if "【要確認】" in text:
        violations.append(f"[段落{i+1}] 【要確認】マークが残っています: {text[:80]}")

print(f"総チェック段落数: {len([p for p in doc.paragraphs if p.text.strip()])}")
print(f"違反件数: {len(violations)}")
for v in violations:
    print(f"  {v}")
```

### ステップ 3: 結果の報告

チェック結果を以下の形式で報告する:

```
## verify-minutes 結果

ファイル: <docx_path>
総段落数: N
違反件数: M

### 発見された問題
1. [段落XX] ...
2. [段落YY] ...

### 問題なし
- 発言行フォーマット: OK / N件の違反
- 半角文字混入: OK / N件の違反
- 発言者間空行: OK / N件の違反
- 傍聴行フォーマット: OK / N件の違反
- 【要確認】マーク: OK / N件残存
```

### ステップ 4: 自動修正の提案

違反が見つかった場合、以下を確認する:

「自動修正できる問題が N 件あります。以下の修正を適用しますか？

（修正内容を箇条書きで表示）

※ 複雑な問題（発言者の誤検出など）は手動での確認が必要です。」

### ステップ 5: 自動修正の実行（ユーザー確認後）

ユーザーが「はい」と答えた場合のみ、以下の自動修正を適用する:

- 発言者間の空行（空段落）の削除
- 【要確認】マークのハイライト表示（削除はしない、ユーザーに確認を促す）

修正後は再度チェックを実行して結果を報告する。
