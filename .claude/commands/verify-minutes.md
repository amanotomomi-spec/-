# verify-minutes

生成した議事録 Word ファイルを Gem指示書・表記ルール統一基準・予算部分表記指示書のフォーマットルールに従って検証します。

## 手順

### ステップ 1: ファイルパスの確認

ユーザーに確認する:
- **検証する .docx パス**: 例 `samples/003/output/minutes.docx`
- **対応する config.yaml パス**: 例 `samples/003/input/config.yaml`（拡張チェックに使用）

### ステップ 2: フォーマットチェックの実行

python-docx を使って以下を一括チェックする:

```python
from docx import Document
import re
import yaml

doc = Document("<docx_path>")
config = yaml.safe_load(open("<config_yaml_path>", encoding="utf-8"))
violations = []

# 拡張チェック用に config から既知の氏名・日程・補正リストを抽出
known_names: set[str] = set()
NAME_RE = re.compile(r'[一-龥々]+(?:　[一-龥々]+)?君')
for section in ("speakers", "members", "extra_corrections"):
    pass  # 下のループでまとめて処理

def collect_names(value):
    if isinstance(value, str):
        known_names.update(NAME_RE.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            collect_names(v)
    elif isinstance(value, list):
        for v in value:
            collect_names(v)

collect_names(config.get("speakers", {}))
collect_names(config.get("members", {}))

agenda_items = config.get("agenda_items", [])
extra_corrections = config.get("extra_corrections", [])

body_texts = [p.text for p in doc.paragraphs]
full_text = "\n".join(body_texts)

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

    # チェック 6: 発言者氏名が config.yaml の登録名と一致するか
    if text.startswith("〇") or text.startswith("○"):
        m = re.search(r'[（(](.+?)[）)]', text)
        if m:
            speaker_names = NAME_RE.findall(m.group(1))
            for name in speaker_names:
                if known_names and name not in known_names:
                    violations.append(f"[段落{i+1}] config.yamlに未登録の発言者名: 「{name}」 「{text[:50]}」")

# チェック 7: 議事日程（agenda_items）が本文に過不足なく順序通り出現するか
last_index = -1
for item in agenda_items:
    # "日程第N　タイトル" のスペース表記ゆれを吸収
    item_norm = re.sub(r'\s+', '', item)
    found_index = None
    for i, t in enumerate(body_texts):
        if re.sub(r'\s+', '', t) == item_norm or item_norm in re.sub(r'\s+', '', t):
            found_index = i
            break
    if found_index is None:
        violations.append(f"[議事日程] 本文に見つかりません: 「{item}」")
    elif found_index <= last_index:
        violations.append(f"[議事日程] 順序が前後しています: 「{item}」（段落{found_index+1}）")
    else:
        last_index = found_index

# チェック 8: extra_corrections の誤変換パターンが修正されずに残っていないか
for wrong, correct in extra_corrections:
    if wrong and wrong in full_text:
        violations.append(f"[誤変換残存] 未修正の誤変換が見つかりました: 「{wrong}」→「{correct}」")

# チェック 9: 表記ルール統一基準・予算部分表記指示書に基づく数値表記チェック
# 「千円」表記は予算部分表記指示書により「万円」へ換算されているはずなので残存していないか確認
for i, text in enumerate(body_texts):
    if re.search(r'[０-９0-9]+千円', text):
        violations.append(f"[段落{i+1}] 「千円」表記が残っています（予算部分表記指示書に基づき要確認）: {text[:50]}")

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
config: <config_yaml_path>
総段落数: N
違反件数: M

### 発見された問題
1. [段落XX] ...
2. [段落YY] ...

### チェック結果サマリー
- 発言行フォーマット: OK / N件の違反
- 半角文字混入: OK / N件の違反
- 発言者間空行: OK / N件の違反
- 傍聴行フォーマット: OK / N件の違反
- 【要確認】マーク: OK / N件残存
- 発言者氏名のconfig照合: OK / N件の違反
- 議事日程の整合性（過不足・順序）: OK / N件の違反
- extra_corrections未修正残存: OK / N件の違反
- 予算金額表記（千円残存等）: OK / N件の違反
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
