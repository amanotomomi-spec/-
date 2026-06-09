"""
Nottaが出力するTXTファイルを解析し、発言者ラベル付きの段落リストを返す。
発言者情報がないため、キーワードルールで推定する。
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meeting_config import MeetingConfig


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
    ("意義なしと認めます", "異議なしと認めます"),
    ("不足といたしまして", "附則といたしまして"),
    ("不足。", "附則。"),
    ("期日全員", "起立全員"),
    ("初版の報告", "諸般の報告"),
    ("クラブ社長", ""),  # 誤認識ノイズ除去
    ("ク村長", ""),      # 発言者ラベルとして処理済み
    ("小木村長", ""),
    ("黒木村長、", ""),
    ("そし。", ""),
    # 工事・建設用語の誤変換（ユーザー修正フィードバック 2026-06-09）
    ("のり弁、およびド派部分", "法面及び法面部分"),
    ("ののり弁", "の法面"),
    ("植生シート高", "植生シート工"),
    ("切土のり面の吹き付け面積", "切土法面の吹き付け面積"),
    ("土は、部分の針箱", "法面部分の種箱"),
    ("工事受変更契約", "工事請負変更契約"),
    ("公事由給与変更、契約", "工事請負変更契約"),
    ("こじ形容変更契約", "工事請負変更契約"),
    ("のり面整形に伴う吹き付け面積の像", "法面整形に伴う吹き付け面積の増"),
    ("現場吹き付けど、学校が", "現場吹付工が"),
    ("平米", "㎡"),
    # 予算・財政用語の誤変換（ユーザー修正フィードバック 2026-06-09）
    ("免許、繰越免許補正は、第２票", "繰越明許費補正は、第２表"),
    ("免許繰り越し", "繰越明許"),
    ("名曲越し", "繰越明許"),
    ("第３票地方裁補正", "第３表地方債補正"),
    ("菅野純一地方交付税", "款の１１地方交付税"),
    ("そ道改良舗装事業", "村道改良舗装事業"),
    ("そ道し、新設改良保障事業", "村道新設改良舗装事業"),
    ("かの重災害復旧費", "款の９災害復旧費"),
    ("減税分が、", "前年度分が、"),
    ("可年度分", "当年度分"),
    ("特攻", "特交"),
    # 固有名詞・事業名の誤変換（ユーザー修正フィードバック 2026-06-09）
    ("シバシイタケ再生計画支援事業", "椎葉椎茸再生計画支援事業"),
    ("投資口、災害", "頭首工災害"),
    ("大河内地区の投資口", "大河内地区の頭首工"),
    ("本村国語運営協議会", "本村国保運営協議会"),
    # 議事進行用語の誤変換（ユーザー修正フィードバック 2026-06-09）
    ("すべて議論しました", "すべて議了しました"),
    ("一度レ、", "一同、礼。"),
    ("これよりすぐに入ります", "これより質疑に入ります"),
    ("尊重の報告を求めます", "諸般の報告を求めます"),
    ("正しい、頑張っていきたい", "精一杯、頑張っていきたい"),
    # 数字の誤変換
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
    ("地方自治第170九条第一項", "地方自治法第179条第１項"),
    ("地方自称第170九条第一項", "地方自治法第179条第１項"),
]


# ======================================================
# 発言者検出ルール（優先度順）
# ======================================================

# ルール1: 段落冒頭に役職名が明示されているパターン
PREFIX_RULES: list[tuple[str, str]] = [
    # 役職名+氏名 or 氏名+役職名 で始まるパターン（区切り文字不要）
    (r"^(黒木)?村長[、,はいえ　]", "村長"),
    (r"^黒木村長", "村長"),      # 区切りなし（例: 黒木村長手入れの…）
    (r"^ク村長", "村長"),        # OCR誤認識
    (r"^小木村長", "村長"),      # OCR誤認識
    (r"^クラブ社長", "村長"),    # OCR誤認識
    (r"^総務課長[、,はいえ　]", "総務課長"),
    (r"^(松岡)?総務課長", "総務課長"),
    (r"^建設課長[、,はいえ　]", "建設課長"),
    (r"^(椎葉)?建設課長", "建設課長"),
    (r"^地域振興課長[、,はいえ　]", "地域振興課長"),
    (r"^副村長[、,はいえ　]", "副村長"),
    (r"^(椎葉)?副村長", "副村長"),
    (r"^事務局長[、,はいえ　]", "事務局長"),
    (r"^会計管理者[、,はいえ　]", "会計管理者"),
    # 役職名のみで始まる（区切りなし含む）
    (r"^農林振興課長", "農林振興課長"),
    (r"^(中瀬)?農林振興課長", "農林振興課長"),
    (r"^福祉保健課長", "福祉保健課長"),
    (r"^病院事務長", "病院事務長"),
    (r"^教育課長", "教育課長"),
    (r"^税務住民課長", "税務住民課長"),
    # 教育長（名前の誤認識に対応: 柚木→猪木等）
    (r"^.{0,3}教育長", "教育長"),
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
    (r"原案のとお(り|て)(承認|可決|同意)", "議長"),
    (r"原案の通り(承認|可決|同意)", "議長"),
    (r"(ご|御)異議ありませんか", "議長"),
    (r"異議なしと認めます", "議長"),
    (r"これをもちまして", "議長"),
    (r"令和\d+年.{1,20}(臨時会|定例会)を(開会|閉会)", "議長"),
    (r"直ちに会議を開きます", "議長"),
    (r"一括して質疑を行います", "議長"),
    (r"逐次討論採決を行います", "議長"),
    (r"会期は本日一日限りと決定", "議長"),
    (r"以上で(諸般|初版)の報告を終わります", "議長"),
    (r"(一般質問|同意|同位).{1,10}の登壇を(求めます|お願いいたします)", "議長"),
    (r"の質問を終わります", "議長"),
    (r"逐次討論を討論採決を行います", "議長"),
    (r"これより逐次", "議長"),
    (r"以上で、本日の日程はすべて終了", "議長"),
    (r"定例会\d+日目は", "議長"),
    (r"会期は.{1,10}[日間]に決定", "議長"),
    # 村長
    (r"(承認|証人)第\d+号.{1,20}提案理", "村長"),
    (r"議案第\d+号.{1,20}提案理", "村長"),
    (r"同意第\d+号.{1,20}提案", "村長"),
    (r"第\d+回椎葉村議会.{1,10}ご出席をいただきまして", "村長"),
    (r"(6月|令和\d+年度)定例会にご出席", "村長"),
    (r"報告第\d+号(専決処分|令和)", "村長"),
    (r"歳入歳出それぞれ.{1,30}追加し、総予算", "村長"),
    (r"繰越明許費補正は、第[２2]表", "村長"),
    (r"詳細は、総務課長が御説明を申し上げます", "村長"),
    (r"(収益的収入及び支出の予定額|歳入歳出それぞれ).{1,30}(減額|増額)でございます", "村長"),
    (r"地方自治法第179条の規定により、令和\d+年\d+月\d+日に専決", "村長"),
    (r"地方自治170九条の規定により.{1,20}専決", "村長"),
    (r"ご審議のほど、よろしくお願い(いたします|申し上げます)", "村長"),
    (r"\d番\w+議員のご質問にお答えいたしたいと思います", "村長"),
    (r"\d番\w+議員のご質問にお答えします", "村長"),
    (r"ご質問の.{1,5}点目.{1,20}についてお答えします", "村長"),
    # 総務課長
    (r"歳入歳出の明細につきまして", "総務課長"),
    (r"予算書の\d+ページをお開きください", "総務課長"),
    (r"(川口|河口)議員のご質問に.{1,15}交付税", "総務課長"),
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
    (r"椎葉(誠也|聖哉)です", "会計管理者"),
    # 議長（開会前の起立指示）
    (r"皆様、ご起立願います。一度ご着席ください", "議長"),
    # 事務局長（開会礼の起立指示、冒頭断片にも対応）
    (r"一同、礼。ご着席ください", "事務局長"),
    (r"^います。一同", "事務局長"),
]

# 傍聴・起立行に変換するパターン
AUDIENCE_PATTERNS: list[tuple[str, str]] = [
    (r"(「?異議なし」?と呼ぶ者あり)", "（「異議なし」と呼ぶ者あり）"),
    (r"(「?討論なし」?と呼ぶ者あり)", "（「討論なし」と呼ぶ者あり）"),
    (r"(「?反対討論なし」?と呼ぶ者あり)", "（「反対討論なし」と呼ぶ者あり）"),
    (r"(「?賛成討論なし」?と呼ぶ者あり)", "（「賛成討論なし」と呼ぶ者あり）"),
    (r"(「?質疑なし」?と呼ぶ者あり)", "（「質疑なし」と呼ぶ者あり）"),
]


def apply_corrections(
    text: str, extra: list[tuple[str, str]] | None = None
) -> str:
    corrections = extra if extra is not None else CORRECTIONS
    for wrong, correct in corrections:
        text = text.replace(wrong, correct)
    return text


def strip_prefix_role(text: str) -> str:
    """冒頭の役職名ラベルを除去する（例: "総務課長、それでは…" → "それでは…"）"""
    pattern = (
        r"^(総務課長|建設課長|地域振興課長|副村長|事務局長|農林振興課長|福祉保健課長"
        r"|病院事務長|教育課長|税務住民課長|会計管理者"
        r"|黒木村長|ク村長|小木村長|クラブ社長|村長"
        r"|.{0,3}教育長)"
        r"[、,はいえ　]?\s*"
    )
    return re.sub(pattern, "", text).strip()


def _build_dynamic_prefix_rules(
    speaker_map: dict[str, str]
) -> list[tuple[str, str]]:
    """configのspeakersから動的にPREFIX_RULESを生成する。"""
    rules: list[tuple[str, str]] = []
    for role_key, formatted in speaker_map.items():
        # "〇教育長（柚木　和浩君）" → role_label="教育長", family="柚木"
        # "〇議員（２番　藏座　二九生君）" → role_label="議員", family="２番"
        m = re.match(r"〇([^（]+)（([^　）]+)", formatted)
        if not m:
            continue
        role_label = m.group(1).strip()  # 教育長, 農林振興課長, 議員 etc.
        first_part = m.group(2).strip()  # 柚木, ２番 etc.

        if role_label == "議員":
            # 議員: 番号で識別
            m_num = re.match(r"([０-９\d]+)番", first_part)
            if m_num:
                num_z = m_num.group(1)
                # 全角→半角変換
                num_h = str(int(num_z.translate(str.maketrans("０１２３４５６７８９", "0123456789"))))
                # 議員名を抽出（姓のみ）
                m_name = re.search(r"（[^　]+　([^\s　君）]+)", formatted)
                family = m_name.group(1) if m_name else ""
                # 番号 + 姓 or 番号のみで識別
                if family:
                    rules.append((rf"^{num_h}番{re.escape(family)}", role_key))
                    rules.append((rf"^{num_z}番{re.escape(family)}", role_key))
                rules.append((rf"^{num_h}番[^（）議長村長副]{{0,10}}議員", role_key))
                rules.append((rf"^{num_z}番[^（）議長村長副]{{0,10}}議員", role_key))
        else:
            # 役職者: 姓+役職 or 役職のみ
            rules.append((rf"^{re.escape(first_part)}{re.escape(role_label)}", role_key))
            # 役職のみ（区切り不要）
            rules.append((rf"^{re.escape(role_label)}[、,　はいえ]", role_key))

    return rules


def detect_speaker(
    text: str, prev_speaker: str, speaker_map: dict[str, str] | None = None
) -> str:
    """段落から発言者を推定する。speaker_mapが指定された場合はそちらを優先する。"""
    effective_map = speaker_map if speaker_map is not None else SPEAKER

    # ルール0: configから動的生成されたプレフィックスルール（より具体的なので先に評価）
    if speaker_map:
        dynamic_rules = _build_dynamic_prefix_rules(speaker_map)
        for pattern, role in dynamic_rules:
            if re.match(pattern, text) and role in effective_map:
                return effective_map[role]

    # ルール1: 冒頭に役職名
    for pattern, role in PREFIX_RULES:
        if re.match(pattern, text):
            if role in effective_map:
                return effective_map[role]

    # ルール2: 内容キーワード
    for pattern, role in CONTENT_RULES:
        if re.search(pattern, text):
            if role in effective_map:
                return effective_map[role]

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
    旧APIとの互換性のために残す。split_procedural_sequence へ委譲。
    """
    return split_procedural_sequence(text)


# 議事進行の傍聴行自動挿入パターン
# (質問パターン, 認定パターン, 挿入する傍聴行テキスト)
PROCEDURAL_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"(ご|御)異議ありませんか[。、？?]?",
        r"異議なしと認めます",
        "（「異議なし」と呼ぶ者あり）",
    ),
    (
        r"質疑はありませんか[。、？?]?",
        r"質疑なしと認めます",
        "（「質疑なし」と呼ぶ者あり）",
    ),
    (
        r"反対討論はありませんか[。、？?]?",
        r"反対討論なしと認めます",
        "（「反対討論なし」と呼ぶ者あり）",
    ),
    (
        r"賛成討論はありませんか[。、？?]?",
        r"賛成討論なしと認めます",
        "（「賛成討論なし」と呼ぶ者あり）",
    ),
    (
        r"討論はありませんか[。、？?]?",
        r"討論なしと認めます",
        "（「討論なし」と呼ぶ者あり）",
    ),
]


def split_procedural_sequence(text: str) -> list[tuple[str, str | None]]:
    """
    議事進行パターン（起立・傍聴行）を含む長い段落を分割して傍聴行を挿入する。

    対応パターン:
    - 「ご起立願います。…ご着席ください。起立全員であります。」 → （賛成者起立）を挿入
    - 「ご異議ありませんか？…異議なしと認めます」 → 傍聴行を間に挿入
    - 「質疑はありませんか？…質疑なしと認めます」 → 傍聴行を間に挿入
    - 「反対討論はありませんか？…反対討論なしと認めます」 → 傍聴行を間に挿入
    - 「賛成討論はありませんか？…賛成討論なしと認めます」 → 傍聴行を間に挿入
    - 「討論はありませんか？…討論なしと認めます」 → 傍聴行を間に挿入

    戻り値: (content_or_audience, "speech"|"audience") のリスト
    """
    results: list[tuple[str, str | None]] = []
    remaining = text

    changed = True
    while changed:
        changed = False

        # --- 起立パターン ---
        vote_pattern = r"((御|ご)起立願います[。、]?)(.*?)(ご着席ください[。、]?)(.*?)(起立全員|規律全員|期日全員)であります"
        m = re.search(vote_pattern, remaining, re.DOTALL)
        if m:
            before = remaining[:m.start()].strip()
            after = remaining[m.end():].strip()
            if before:
                results.append((before, "speech"))
            results.append(("（賛成者起立）", "audience"))
            suffix = "ご着席ください。起立全員であります。"
            remaining = (suffix + after) if after else suffix
            changed = True
            continue

        # --- 傍聴行パターン（質疑・討論・異議）---
        for ask_pat, confirm_pat, audience_text in PROCEDURAL_PATTERNS:
            m_ask = re.search(ask_pat, remaining)
            if not m_ask:
                continue
            # 確認フレーズが質問フレーズより後にあるか
            m_confirm = re.search(confirm_pat, remaining[m_ask.end():])
            if not m_confirm:
                continue
            confirm_start = m_ask.end() + m_confirm.start()
            # 質問フレーズ末尾 ~ 確認フレーズ先頭の間にテキストが少ない場合のみ分割
            # （別人の発言が挟まる可能性を避けるため200文字以内）
            gap = remaining[m_ask.end():confirm_start]
            if len(gap) > 200:
                continue
            # 分割点: 質問フレーズ末尾で分割
            split_at = m_ask.end()
            before = remaining[:split_at].strip()
            after = remaining[split_at:].strip()
            if before:
                results.append((before, "speech"))
            results.append((audience_text, "audience"))
            remaining = after
            changed = True
            break

    if remaining.strip():
        results.append((remaining.strip(), "speech"))

    return results if results else [(text, "speech")]


# 漢数字→全角アラビア数字マッピング（日程番号用）
KANJI_NUM_MAP: dict[str, str] = {
    "一": "１", "二": "２", "三": "３", "四": "４", "五": "５",
    "六": "６", "七": "７", "八": "８", "九": "９",
    "十一": "１１", "十二": "１２", "十三": "１３", "十四": "１４", "十五": "１５",
    "十六": "１６", "十七": "１７", "十八": "１８", "十九": "１９",
    "十": "１０", "二十": "２０",
}


def convert_kanji_agenda_num(text: str) -> str:
    """「日程第X」のXが漢数字の場合、全角アラビア数字に変換する。"""
    def replace_num(m: re.Match) -> str:
        kanji = m.group(1)
        arabic = KANJI_NUM_MAP.get(kanji, kanji)
        return f"日程第{arabic}"

    # 二十より先に二十X系、十X系を処理するため長い順にソート済みのKANJI_NUM_MAPを使う
    # re.subで一度に処理するためにパターンを組み立てる
    kanji_keys = sorted(KANJI_NUM_MAP.keys(), key=len, reverse=True)
    pattern = r"日程第(" + "|".join(re.escape(k) for k in kanji_keys) + r")"
    return re.sub(pattern, replace_num, text)


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
    # 事務局長→議長の引き継ぎ（礼の後）
    # "います。一同、礼。ご着席ください。おはようございます..." の冒頭は事務局長、礼以降は議長
    m_rei = re.search(r"(一同、礼。ご着席ください。)", text)
    if m_rei:
        before = text[:m_rei.end()].strip()
        after = text[m_rei.end():].strip()
        if before and after:
            return [before, after]

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


def parse_notta_txt(
    path: str, config: "MeetingConfig | None" = None
) -> list[dict]:
    """
    NottaのTXTファイルを解析し、発言ブロックのリストを返す。
    各ブロック:
      {"type": "speech",    "speaker": str, "content": str}
      {"type": "audience",  "content": str}
      {"type": "agenda",    "content": str}  ← 日程見出し

    config が指定された場合:
      - config.speakers で発言者マッピングを上書き
      - config.extra_corrections を追加補正辞書として使用
    """
    # configが指定されたとき追加補正を適用するための補正リスト構築
    effective_corrections = list(CORRECTIONS)
    speaker_map: dict[str, str] | None = None
    if config is not None:
        effective_corrections = effective_corrections + list(config.extra_corrections)
        if config.speakers:
            speaker_map = config.speakers

    raw = Path(path).read_text(encoding="utf-8")

    # 段落に分割（ダブル改行区切り）
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]

    blocks: list[dict] = []
    prev_speaker = ""

    for para in paragraphs:
        # テキスト補正
        para = apply_corrections(para, extra=effective_corrections if config is not None else None)

        # 空段落スキップ
        if not para:
            continue

        # 複数発言者が混在する段落を分割
        sub_paras = split_multi_speaker_para(para)

        for sub_para in sub_paras:
            sub_para = sub_para.strip()
            if not sub_para:
                continue

            # 漢数字の日程番号を全角アラビア数字に変換
            sub_para = convert_kanji_agenda_num(sub_para)

            # 日程見出し検出（短い段落 or 長い発言の先頭が「日程第X」で始まる場合も対応）
            m_agenda = re.match(
                r"^(日程第[１２３４５６７８９０\d]+[　\s]\S.*?)([。　\s]|$)", sub_para
            )
            if not m_agenda:
                # 短い段落の検出（旧動作互換）
                m_agenda_old = re.search(
                    r"日程第(\d+|[１２３４５６７８９０]+)[　\s]", sub_para
                )
                if m_agenda_old and len(sub_para) < 60:
                    content = to_zenkaku(sub_para)
                    blocks.append({"type": "agenda", "content": content})
                    continue

            if m_agenda:
                # 「日程第X　タイトル」の先頭部分からagendaブロックを生成
                # config.agenda_itemsから正式なタイトルを探す
                agenda_num_m = re.match(r"日程第([１２３４５６７８９０\d]+)", sub_para)
                agenda_title = None
                if agenda_num_m and config is not None and hasattr(config, "agenda_items"):
                    num_str = agenda_num_m.group(1)
                    # 全角数字→半角数字に変換して比較
                    num_h = str(int(num_str.translate(str.maketrans("０１２３４５６７８９", "0123456789"))))
                    for item in config.agenda_items:
                        item_m = re.match(r"日程第\s*(\d+)", item)
                        if item_m and item_m.group(1) == num_h:
                            agenda_title = item
                            break
                if agenda_title is None:
                    # configにない場合は発言から先頭の日程見出し部分を使う
                    # 「日程第X、内容を議題とします」→「日程第X　内容」
                    agenda_title_m = re.match(
                        r"(日程第[１２３４５６７８９０\d]+)[　\s、,](.{1,40}?)(?:[をは]議題|[をは]行います|[。、]|$)",
                        sub_para,
                    )
                    if agenda_title_m:
                        agenda_title = f"{agenda_title_m.group(1)}　{agenda_title_m.group(2)}"
                    else:
                        agenda_title = sub_para[:60]

                blocks.append({"type": "agenda", "content": agenda_title})

                # 短い段落（見出しのみ）ならここで終了
                if len(sub_para) < 60:
                    continue
                # 長い発言の場合は続きのテキストも処理する（発言はそのまま残す）

            # 発言者検出
            speaker = detect_speaker(sub_para, prev_speaker, speaker_map)

            # 役職冒頭ラベル除去
            content = strip_prefix_role(sub_para)

            # 採決フロー分割
            sub_items = split_procedural_sequence(content)

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
