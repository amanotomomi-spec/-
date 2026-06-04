"""
Nottaが出力するTXTファイルを解析し、発言者ラベル付きの段落リストを返す。
発言者情報がないため、キーワードルールで推定する。
"""
import re
from pathlib import Path


# ======================================================
# 発言者の正式表記
# ======================================================
SPEAKER = {
    "議長": "〇議長（岡村　正司君）",
    "村長": "〇村長（黒木　保隆君）",
    "総務課長": "〇総務課長（松岡　正社君）",
    "建設課長": "〇建設課長（椎葉　友和君）",
    "地域振興課長": "〇地域振興課長（甲斐　卓人君）",
    "副村長": "〇副村長（椎葉　和博君）",
    "会計管理者": "〇会計管理者（椎葉　誠也君）",
    "河口議員": "〇議員（５番　河口　吉弘君）",
    "事務局長": "〇議会事務局長（甲斐　万寿也君）",
}

UNKNOWN = "【要確認：発言者不明】"


# ======================================================
# テキスト誤変換の補正辞書
# ======================================================
CORRECTIONS: list[tuple[str, str]] = [
    # 冒頭の誤変換（会議開始前の事務局長発言）
    ("記事にし、一度でい、無着せてください", "皆様、ご起立願います。一度ご着席ください"),
    ("実席から失礼します", "席上から失礼します"),
    # 固有名詞の誤変換
    ("証人第", "承認第"),
    ("商人第", "承認第"),
    ("小人第", "承認第"),
    ("法案は", "本案は"),
    ("停止者の説明", "提案者の説明"),
    ("提示さんの説明", "提案者の説明"),
    ("提示さの説明", "提案者の説明"),
    ("停車の説明", "提案者の説明"),
    ("規律全員", "起立全員"),
    ("ごしください", "ご着席ください"),
    ("ご着席ください。規律全員", "ご着席ください。起立全員"),
    ("国立願います", "ご起立願います"),
    ("御記述願います", "ご起立願います"),
    ("御議願います", "ご起立願います"),
    ("御議決願います", "ご起立願います"),
    ("ご記述願います", "ご起立願います"),
    ("御起立願います", "ご起立願います"),
    ("お分かりします", "お諮りします"),
    ("ご意議ありませんか", "ご異議ありませんか"),
    ("不足といたしまして", "附則といたしまして"),
    ("不足。", "附則。"),
    ("期日全員", "起立全員"),
    ("初版の報告", "諸般の報告"),
    ("クラブ社長", ""),  # 誤認識ノイズ除去
    ("ク村長", ""),      # 発言者ラベルとして処理済み
    ("小木村長", ""),
    ("黒木村長、", ""),
    ("そし。", ""),
    ("そし。", ""),
    # 数字の誤変換
    ("令和4年度", "令和7年度"),  # この会議は令和7年度補正が対象
    ("第170九条", "第179条"),
    ("第108十条", "第180条"),
    ("第110三条", "第113条"),
    ("地方実施第96条", "地方自治法第96条"),
    ("地方実証第96条", "地方自治法第96条"),
    ("地方自称第170九条", "地方自治法第179条"),
    ("地方自治第170九条", "地方自治法第179条"),
    ("地方自書170九条", "地方自治法第179条"),
    ("長治正第170九条", "地方自治法第179条"),
    ("地方自治170九条", "地方自治法第179条"),
    ("地方自法第108十条", "地方自治法第180条"),
]


# ======================================================
# 発言者検出ルール（優先度順）
# ======================================================

# ルール1: 段落冒頭に役職名が明示されているパターン
PREFIX_RULES: list[tuple[str, str]] = [
    (r"^総務課長[、,はい]", "総務課長"),
    (r"^建設課長[、,]", "建設課長"),
    (r"^地域振興課長[、,]", "地域振興課長"),
    (r"^副村長[、,]", "副村長"),
    (r"^事務局長[、,]", "事務局長"),
    (r"^(黒木)?村長[、,はい]", "村長"),
    (r"^ク村長", "村長"),        # OCR誤認識
    (r"^小木村長", "村長"),      # OCR誤認識
    (r"^クラブ社長", "村長"),    # OCR誤認識
]

# ルール2: 発言内容から推定するパターン
CONTENT_RULES: list[tuple[str, str]] = [
    # 議長
    (r"ただいまから令和\d+年", "議長"),
    (r"会議を開く前に", "議長"),
    (r"日程第.{1,5}[、、を]議題とします", "議長"),
    (r"日程第.{1,5}[、、を]行います", "議長"),
    (r"提案者の説明を求めます", "議長"),
    (r"説明が終わりました", "議長"),
    (r"これより質疑に入ります", "議長"),
    (r"質疑はありませんか", "議長"),
    (r"質疑なしと認めます", "議長"),
    (r"これより討論を行います", "議長"),
    (r"討論はありませんか", "議長"),
    (r"討論なしと認めます", "議長"),
    (r"これから採決を行います", "議長"),
    (r"(御|ご)起立願います", "議長"),
    (r"(起立|規律|期日)全員であります", "議長"),
    (r"原案のとお(り|て)(承認|可決)", "議長"),
    (r"原案の通り(承認|可決)", "議長"),
    (r"(ご|御)異議ありませんか", "議長"),
    (r"異議なしと認めます", "議長"),
    (r"これをもちまして", "議長"),
    (r"令和\d+年.{1,10}臨時会を(開会|閉会)", "議長"),
    (r"直ちに会議を開きます", "議長"),
    (r"一括して質疑を行います", "議長"),
    (r"逐次討論採決を行います", "議長"),
    (r"会期は本日一日限りと決定", "議長"),
    (r"以上で(諸般|初版)の報告を終わります", "議長"),
    # 村長
    (r"(承認|証人)第\d+号.{1,20}提案理", "村長"),
    (r"議案第\d+号.{1,20}提案理", "村長"),
    (r"第\d+回椎葉村議会.{1,10}ご出席をいただきまして", "村長"),
    (r"報告第\d+号専決処分", "村長"),
    (r"歳入歳出それぞれ.{1,30}追加し、総予算", "村長"),
    (r"繰越明許費補正は、第[２2]表", "村長"),
    (r"詳細は、総務課長が御説明を申し上げます", "村長"),
    (r"(収益的収入及び支出の予定額|歳入歳出それぞれ).{1,30}(減額|増額)でございます", "村長"),
    (r"地方自治法第179条の規定により、令和\d+年\d+月\d+日に専決", "村長"),
    (r"地方自治170九条の規定により.{1,20}専決", "村長"),
    (r"ご審議のほど、よろしくお願い(いたします|申し上げます)", "村長"),
    # 総務課長
    (r"歳入歳出の明細につきまして", "総務課長"),
    (r"予算書の\d+ページをお開きください", "総務課長"),
    (r"川口議員のご質問に.{1,15}交付税", "総務課長"),
    (r"集落支援の分も.{1,20}含まれておりますので", "総務課長"),
    # 建設課長
    (r"土地(払い)?建物(を)?払い", "建設課長"),
    (r"土地建物の払い下げ", "建設課長"),
    # 地域振興課長
    (r"移住定住促進.{1,15}住環境整備事業に関して", "地域振興課長"),
    (r"5番川口議員の第3点目", "地域振興課長"),
    # 河口議員
    (r"\d点についてですね.{1,20}質疑をいたしたいと思います", "河口議員"),
    (r"まず、第一点でございますけれども", "河口議員"),
    (r"申請以上に交付税がつく", "河口議員"),
    (r"ちほど資料をいただける", "河口議員"),
    (r"集落支援員相当な", "河口議員"),
    # 会計管理者
    (r"出納室、会計管理者を拝命いたしました", "会計管理者"),
    (r"椎葉誠也です", "会計管理者"),
    # 議長（開会前の起立指示）
    (r"皆様、ご起立願います。一度ご着席ください", "議長"),
]

# 傍聴・起立行に変換するパターン
AUDIENCE_PATTERNS: list[tuple[str, str]] = [
    (r"(「?異議なし」?と呼ぶ者あり)", "（「異議なし」と呼ぶ者あり）"),
    (r"(「?討論なし」?と呼ぶ者あり)", "（「討論なし」と呼ぶ者あり）"),
    (r"(「?反対討論なし」?と呼ぶ者あり)", "（「反対討論なし」と呼ぶ者あり）"),
    (r"(「?賛成討論なし」?と呼ぶ者あり)", "（「賛成討論なし」と呼ぶ者あり）"),
    (r"(「?質疑なし」?と呼ぶ者あり)", "（「質疑なし」と呼ぶ者あり）"),
]


def apply_corrections(text: str) -> str:
    for wrong, correct in CORRECTIONS:
        text = text.replace(wrong, correct)
    return text


def strip_prefix_role(text: str) -> str:
    """冒頭の役職名ラベルを除去する（例: "総務課長、それでは…" → "それでは…"）"""
    pattern = r"^(総務課長|建設課長|地域振興課長|副村長|事務局長|黒木村長|ク村長|小木村長|クラブ社長|村長)[、,はいえ]?\s*"
    return re.sub(pattern, "", text).strip()


def detect_speaker(text: str, prev_speaker: str) -> str:
    """段落から発言者を推定する。"""
    # ルール1: 冒頭に役職名
    for pattern, role in PREFIX_RULES:
        if re.match(pattern, text):
            return SPEAKER[role]

    # ルール2: 内容キーワード
    for pattern, role in CONTENT_RULES:
        if re.search(pattern, text):
            return SPEAKER[role]

    # ルール3: 前の発言者を継続
    if prev_speaker and prev_speaker != UNKNOWN:
        return prev_speaker

    return UNKNOWN


def is_audience_text(text: str) -> tuple[bool, str]:
    """傍聴・起立行かどうか判定し、正規化した表記を返す。"""
    # 単体で傍聴行になるパターン
    if re.search(r"(起立|規律|期日)全員であります", text):
        # 「起立全員」の宣言のみの短い段落
        if len(text) < 20:
            return True, "（賛成者起立）"
    for pattern, normalized in AUDIENCE_PATTERNS:
        if re.search(pattern, text):
            return True, normalized
    return False, ""


def split_vote_sequence(text: str) -> list[tuple[str, str | None]]:
    """
    「討論はありませんか？討論なしと認めます。…採決…御起立願います。ご着席ください。起立全員であります。」
    のような長い段落を、採決フロー部分で分割して傍聴行を挿入する。
    戻り値: (content_or_audience, speaker_or_None) のリスト
    """
    results: list[tuple[str, str | None]] = []

    # 起立～着席のパターンで分割
    pattern = r"((御|ご)起立願います[。、]?)(.*?)(ご着席ください[。、]?)(.*?)(起立全員|規律全員|期日全員)であります"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        before = text[:m.start()].strip()
        after = text[m.end():].strip()
        if before:
            results.append((before, "speech"))
        results.append(("（賛成者起立）", "audience"))
        if after:
            suffix = "ご着席ください。起立全員であります。" + after
            results.append((suffix, "speech"))
        else:
            results.append(("ご着席ください。起立全員であります。", "speech"))
    else:
        results.append((text, "speech"))

    return results


def to_zenkaku(text: str) -> str:
    """半角英数字・記号を全角に変換。"""
    result = []
    for ch in text:
        code = ord(ch)
        if 0x21 <= code <= 0x7E:
            result.append(chr(code + 0xFEE0))
        elif ch == " ":
            result.append("　")
        else:
            result.append(ch)
    return "".join(result)


def split_multi_speaker_para(text: str) -> list[str]:
    """
    1段落に複数の発言者が混在している場合に分割する。
    「以上、ご報告をいたします。以上で諸般の報告を終わります。日程第…」
    のような議長への引き継ぎ句で分割。
    """
    # 議長への引き継ぎパターン（前後で分割）
    handover_patterns = [
        r"(以上で(諸般|初版)の報告を終わります[。　]?)",
        r"(説明が終わりました[。　]?)",
        r"(以上、ご報告をいたします[。　]?以上で)",
    ]
    for pat in handover_patterns:
        m = re.search(pat, text)
        if m:
            split_pos = m.end()
            before = text[:split_pos].strip()
            after = text[split_pos:].strip()
            if before and after:
                return [before, after]
    return [text]


def parse_notta_txt(path: str) -> list[dict]:
    """
    NottaのTXTファイルを解析し、発言ブロックのリストを返す。
    各ブロック:
      {"type": "speech",    "speaker": str, "content": str}
      {"type": "audience",  "content": str}
      {"type": "agenda",    "content": str}  ← 日程見出し
    """
    raw = Path(path).read_text(encoding="utf-8")

    # 段落に分割（ダブル改行区切り）
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]

    blocks: list[dict] = []
    prev_speaker = ""

    for para in paragraphs:
        # テキスト補正
        para = apply_corrections(para)

        # 空段落スキップ
        if not para:
            continue

        # 複数発言者が混在する段落を分割
        sub_paras = split_multi_speaker_para(para)

        for sub_para in sub_paras:
            sub_para = sub_para.strip()
            if not sub_para:
                continue

            # 日程見出し検出（短い段落のみ）
            m_agenda = re.search(r"日程第(\d+|一|二|三|四|五|六|七|八|九|十[一二三四五]?)[　\s]", sub_para)
            if m_agenda and len(sub_para) < 60:
                content = to_zenkaku(sub_para)
                blocks.append({"type": "agenda", "content": content})
                continue

            # 発言者検出
            speaker = detect_speaker(sub_para, prev_speaker)

            # 役職冒頭ラベル除去
            content = strip_prefix_role(sub_para)

            # 採決フロー分割
            sub_items = split_vote_sequence(content)

            for sub_content, sub_type in sub_items:
                sub_content = sub_content.strip()
                if not sub_content:
                    continue

                if sub_type == "audience":
                    blocks.append({"type": "audience", "content": sub_content})
                    continue

                sub_content = to_zenkaku(sub_content)
                blocks.append({
                    "type": "speech",
                    "speaker": speaker,
                    "content": sub_content,
                })

            prev_speaker = speaker if speaker != UNKNOWN else prev_speaker

    return blocks


def summarize(blocks: list[dict]) -> None:
    """解析結果のサマリーを表示（確認用）。"""
    total = len(blocks)
    unknown = sum(1 for b in blocks if b.get("speaker") == UNKNOWN)
    print(f"総ブロック数: {total}")
    print(f"発言者不明: {unknown} ({unknown/total*100:.1f}%)")
    print()
    print("=== 先頭20ブロック ===")
    for i, b in enumerate(blocks[:20]):
        t = b["type"]
        if t == "speech":
            sp = b["speaker"][:20]
            ct = b["content"][:40]
            print(f"{i:3d} [{t}] {sp} | {ct}…")
        else:
            print(f"{i:3d} [{t}] {b['content'][:60]}")
    if unknown > 0:
        print()
        print("=== 発言者不明ブロック ===")
        for i, b in enumerate(blocks):
            if b.get("speaker") == UNKNOWN:
                print(f"  ブロック{i}: {b['content'][:60]}…")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/002/input/transcribed.txt"
    blocks = parse_notta_txt(path)
    summarize(blocks)
