# generate-minutes

議事録（Word ファイル）を Notta テキストと config.yaml から生成します。

## ⚠️ 必ず守ること
- 生成前に **Gem指示書**（`docs/rules/Gem指示書.txt`）のルールを確認すること
- 生成後に必ず `/verify-minutes` を実行して品質チェックを行うこと
- 問題がある場合はコードを修正してから再生成すること（そのままファイルを送らない）

---

## ステップ 0: 事前チェックリスト（必須）

生成前に以下を確認する:

```
[ ] Gem指示書の主要ルールを把握しているか？
    - 発言行フォーマット: 〇役職名（氏名君）　発言内容（全角スペース1つ）
    - 傍聴行: （「異議なし」と呼ぶ者あり）等が質問→回答の間に自動挿入されるか
    - 日程見出し: 日程が変わるたびに「日程第X　タイトル」行が挿入されるか
    - 漢数字不使用: 日程番号等が全角アラビア数字になっているか
    - 発言内容に半角文字なし: to_zenkaku() が適用されているか
    - 発言者間に空行なし: space_after = Pt(0) が設定されているか

[ ] config.yaml の内容が正しいか？
    - title, date, open_time が正しいか
    - agenda_items が全日程分あるか
    - speakers に全発言者が登録されているか（教育長、農林振興課長等）
    - extra_corrections に会議固有の誤変換補正が入っているか
```

---

## ステップ 1: 入力ファイルの確認

ユーザーに以下を確認してください（未指定の場合はスマートデフォルトを提案する）:

- **Notta TXT パス**: 例 `samples/NNN/input/notta.txt`
- **config.yaml パス**: 例 `samples/NNN/input/config.yaml`
- **出力 docx パス**: 例 `samples/NNN/output/minutes_draft.docx`

ファイルが複数ある場合は結合する:
```bash
# 複数ファイルの結合（必要な場合）
python3 -c "
files = ['file1.txt', 'file2.txt', 'file3.txt']
combined = '\n\n'.join(open(f, encoding='utf-8').read() for f in files)
open('notta_combined.txt', 'w', encoding='utf-8').write(combined)
"
```

---

## ステップ 2: 議事録生成

```bash
python3 src/main_v2.py --notta <notta_txt> --config <config_yaml> --output <output_docx>
```

実行ログを確認し、`⚠️ 発言者不明` の件数を報告する。
不明件数が多い場合（5件以上）はconfig.yamlのspeakersを補完してから再実行する。

---

## ステップ 3: 品質チェック（必須）

生成後、以下のチェックを実行する:

```python
from docx import Document
import re

doc = Document("<output_docx>")
paras = doc.paragraphs

results = {
    "総段落数": len([p for p in paras if p.text.strip()]),
    "発言者不明": [],
    "傍聴行なし疑い": [],
    "日程見出し": [],
    "半角文字混入": [],
    "発言行フォーマット違反": [],
}

for i, p in enumerate(paras):
    t = p.text
    if not t.strip():
        continue

    # 発言者不明
    if "【要確認" in t:
        results["発言者不明"].append(f"段落{i+1}: {t[:60]}")

    # 日程見出し
    if re.match(r"^日程第", t) and "〇" not in t:
        results["日程見出し"].append(f"段落{i+1}: {t[:60]}")

    # 傍聴行確認（〇議長が質問して次の〇議長が回答の間に傍聴行があるか）
    # ※ここでは傍聴行の存在確認のみ
    if re.match(r"^（「.+」と呼ぶ者あり）", t) or t == "（賛成者起立）":
        # カウントは結果に含める
        pass

    # 発言行フォーマット（氏名君 を含む真の発言行のみチェック）
    if (t.startswith("〇") or t.startswith("○")) and "君）" in t:
        if not re.search(r"[）]　", t):
            results["発言行フォーマット違反"].append(f"段落{i+1}: {t[:60]}")
        # 半角文字チェック（発言内容部分のみ）
        m = re.search(r"[）]　(.+)", t)
        if m:
            half = re.findall(r"[!-~]", m.group(1))
            if half:
                results["半角文字混入"].append(f"段落{i+1}: {''.join(half[:15])} 「{t[:50]}」")

# 傍聴行の総数
audience_count = sum(1 for p in paras if re.match(r"^（", p.text.strip()))

print(f"総段落数: {results['総段落数']}")
print(f"日程見出し行数: {len(results['日程見出し'])}")
print(f"傍聴行数: {audience_count}")
print(f"発言者不明: {len(results['発言者不明'])}件")
print(f"発言行フォーマット違反: {len(results['発言行フォーマット違反'])}件")
print(f"半角文字混入: {len(results['半角文字混入'])}件")
if results["発言者不明"]:
    print("\n--- 発言者不明箇所 ---")
    for v in results["発言者不明"]:
        print(f"  {v}")
if results["発言行フォーマット違反"]:
    print("\n--- フォーマット違反 ---")
    for v in results["発言行フォーマット違反"][:10]:
        print(f"  {v}")
if results["半角文字混入"]:
    print("\n--- 半角文字混入 ---")
    for v in results["半角文字混入"][:10]:
        print(f"  {v}")
```

### 品質基準（すべて満たしてからファイル送信）
- [ ] 発言者不明: **0件**
- [ ] 発言行フォーマット違反: **0件**
- [ ] 半角文字混入: **0件**
- [ ] 日程見出し行: **議事日程と同数** あること
- [ ] 傍聴行: **1件以上** あること（異議なし・質疑なし・起立等）

いずれかが基準未達の場合:
1. コードまたはconfig.yamlの問題を特定して修正
2. 再生成してチェックをやり直す
3. 全基準を満たしてからファイル送信する

---

## ステップ 4: ファイルをユーザーに送信

全品質基準を満たした場合のみ SendUserFile で送信する。
送信時に以下を報告する:
- 総段落数
- 日程見出し数 / 傍聴行数
- 発言者不明・違反件数（0件であることを明示）

---

## ステップ 5: フォローアップ

「修正が必要な箇所はありましたか？修正済みファイルがあれば `/learn-corrections` で学習できます。」
