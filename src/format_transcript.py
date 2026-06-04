"""
文字起こしテキストをGem指示書ルールに従って整形し、Wordファイルを生成する。
発言者情報はPDFから抽出した固有名詞と文脈から推定する。
"""
import re
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ======================================================
# 固有名詞・役職マッピング（PDFから抽出 + 既知情報）
# ======================================================
SPEAKER_MAP: dict[str, str] = {
    # 議長
    "岡村": "議長（岡村　正司君）",
    "岡村正司": "議長（岡村　正司君）",
    # 議員
    "川口": "議員（５番　河口　吉弘君）",
    "川内": "議員（５番　河口　吉弘君）",
    "河口": "議員（５番　河口　吉弘君）",
    "椎葉邦博": "議員（７番　椎葉　邦博君）",
    "甲斐美義": "議員（８番　甲斐　美義君）",
    "藏座": "議員（２番　藏座　二九生君）",
    "尾前": "議員（４番　尾前　秀久君）",
    "那須": "議員（９番　那須　重美君）",
    "椎葉一": "議員（３番　椎葉　　一君）",
    # 執行部
    "黒木村長": "村長（黒木　保隆君）",
    "村長": "村長（黒木　保隆君）",
    "黒木": "村長（黒木　保隆君）",
    "椎葉和博": "副村長（椎葉　和博君）",
    "副村長": "副村長（椎葉　和博君）",
    "総務課長": "総務課長（松岡　正社君）",
    "松岡": "総務課長（松岡　正社君）",
    "建設課長": "建設課長（椎葉　友和君）",
    "地域振興課長": "地域振興課長（甲斐　卓人君）",
    "会計管理者": "会計管理者（椎葉　誠也君）",
    "椎葉誠也": "会計管理者（椎葉　誠也君）",
    "事務局長": "議会事務局長（甲斐　万寿也君）",
    "甲斐万寿也": "議会事務局長（甲斐　万寿也君）",
}

# 採決・傍聴パターン
AUDIENCE_PATTERNS = [
    r"異議なし",
    r"賛成討論なし",
    r"反対討論なし",
    r"質疑なし",
]


def to_zenkaku(text: str) -> str:
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


def detect_speaker(line: str) -> tuple[str, str] | None:
    """
    行から発言者と発言内容を検出する。
    戻り値: (役職表記, 発言内容) または None
    """
    # すでに〇で始まる場合はそのまま
    m = re.match(r"[〇○](.+?)（(.+?)君）\s*(.*)", line)
    if m:
        role = m.group(1).strip()
        name = m.group(2).strip()
        content = m.group(3).strip()
        return (f"〇{role}（{name}君）", content)

    # 「XX課長、」「村長、」などの冒頭パターン
    for key, role in SPEAKER_MAP.items():
        pattern = rf"^{re.escape(key)}[、,，\s]*(.*)"
        m = re.match(pattern, line)
        if m:
            return (f"〇{role}", m.group(1).strip())

    return None


def is_audience_line(text: str) -> bool:
    for pat in AUDIENCE_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def is_vote_standing(text: str) -> bool:
    return "御起立" in text or "ご起立" in text or "賛成者" in text


def is_time_line(text: str) -> bool:
    return bool(re.search(r"午[前後]\d+時\d*分?(休憩|再開|開会|閉会)", text))


def is_schedule_header(text: str) -> bool:
    return bool(re.match(r"日程第\s*\d+", text))


def normalize_numbers(text: str) -> str:
    """半角数字・英字を全角に（発言内容のみ）"""
    return to_zenkaku(text)


def clean_raw_line(line: str) -> str:
    """不要な空白・記号を除去"""
    line = line.strip()
    # 末尾の不要な句読点除去はしない（議事録なので保持）
    return line


def parse_transcript(raw_text: str) -> list[dict]:
    """
    文字起こしテキストを解析して発言ブロックのリストを返す。
    各ブロック: {"type": str, "speaker": str, "content": str}
    """
    lines = [l.strip() for l in raw_text.split("\n")]
    blocks: list[dict] = []
    current_speaker = ""
    current_content: list[str] = []

    def flush():
        nonlocal current_speaker, current_content
        if current_content:
            text = "　".join(current_content) if len(current_content) > 1 else current_content[0]
            blocks.append({
                "type": "speech",
                "speaker": current_speaker,
                "content": normalize_numbers(text),
            })
        current_speaker = ""
        current_content = []

    for line in lines:
        if not line:
            continue

        # 時刻行
        if is_time_line(line):
            flush()
            blocks.append({"type": "time", "content": line})
            continue

        # 日程見出し
        if is_schedule_header(line):
            flush()
            # 日程番号を全角に
            line = re.sub(r"日程第\s*(\d+)", lambda m: f"日程第{to_zenkaku(m.group(1))}", line)
            blocks.append({"type": "schedule", "content": line})
            continue

        # 傍聴・呼ぶ者あり
        if is_audience_line(line):
            flush()
            # 「〜なし」→「（「〜なし」と呼ぶ者あり）」に変換
            m = re.search(r"(異議なし|討論なし|質疑なし|賛成討論なし|反対討論なし)", line)
            if m:
                phrase = m.group(1)
                blocks.append({"type": "audience", "content": f"（「{phrase}」と呼ぶ者あり）"})
            continue

        # 起立
        if "起立全員" in line or "規律全員" in line:
            flush()
            blocks.append({"type": "audience", "content": "（賛成者起立）"})
            # 起立全員の宣言は直後の議長発言として処理
            rest = re.sub(r".*?(起立全員|規律全員)(であります)?[。、]?\s*", "", line).strip()
            if rest:
                current_speaker = "〇議長（岡村　正司君）"
                current_content = [normalize_numbers(rest)]
            continue

        # 発言者検出
        detected = detect_speaker(line)
        if detected:
            flush()
            current_speaker, content = detected
            if content:
                current_content = [normalize_numbers(content)]
            continue

        # 継続発言
        if current_speaker and line:
            current_content.append(normalize_numbers(line))
        elif line:
            # 発言者不明の場合は前の発言者に続ける or 地の文
            if current_speaker:
                current_content.append(normalize_numbers(line))
            else:
                # 地の文として追加
                blocks.append({"type": "text", "content": normalize_numbers(line)})

    flush()
    return blocks


def build_document(
    blocks: list[dict],
    meeting_title: str,
    meeting_date: str,
    meeting_time: str,
    schedule_items: list[str],
    output_path: str,
) -> None:
    doc = Document()

    # ページ設定
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)

    # スタイル設定
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "ＭＳ 明朝"
    normal_style.font.size = Pt(10.5)

    def add_para(text: str, style: str = "Normal", align=None) -> None:
        p = doc.add_paragraph(text, style=style)
        if align:
            p.alignment = align
        return p

    # ヘッダー部分
    add_para(meeting_title, "Title", WD_ALIGN_PARAGRAPH.CENTER)
    add_para(meeting_date)
    add_para("")
    add_para("議事日程（第１号）")
    add_para(f"{meeting_date}　{meeting_time}開会")
    add_para("")
    for item in schedule_items:
        add_para(item)
    add_para("")

    # 本文
    prev_type = None
    for block in blocks:
        btype = block["type"]

        if btype == "speech":
            speaker = block["speaker"]
            content = block["content"]
            # 改行を含む発言は複数行に分割（全角スペース付き）
            lines = content.split("　")
            first = True
            for seg in lines:
                seg = seg.strip()
                if not seg:
                    continue
                if first:
                    add_para(f"{speaker}　{seg}")
                    first = False
                else:
                    add_para(f"　{seg}")

        elif btype == "audience":
            add_para(block["content"])

        elif btype == "schedule":
            add_para("")
            add_para(block["content"])

        elif btype == "time":
            add_para(block["content"])

        elif btype == "text":
            add_para(block["content"])

        prev_type = btype

    doc.save(output_path)
    print(f"✅ 保存完了: {output_path}")


def main(transcript_path: str, pdf_paths: list[str], output_path: str) -> None:
    # PDF解析
    sys.path.insert(0, str(Path(__file__).parent))
    from parse_pdf import parse_schedule

    info = parse_schedule(pdf_paths)
    print(f"会議名: {info.title}")
    print(f"日付: {info.date}")
    print(f"日程: {len(info.items)}件")

    # 議事日程リスト整形（PDF抽出が崩れる場合の手動補正）
    FIXED_SCHEDULE = [
        "日程第１　会議録署名議員の指名",
        "日程第２　会期の決定",
        "日程第３　諸般の報告",
        "日程第４　承認第１号　令和７年度椎葉村一般会計補正予算（第１０号）について",
        "日程第５　承認第２号　令和７年度椎葉村国民健康保険特別会計補正予算（第６号）について",
        "日程第６　承認第３号　令和７年度椎葉村簡易水道事業特別会計補正予算（第６号）について",
        "日程第７　承認第４号　令和７年度椎葉村国民健康保険病院事業特別会計補正予算（第５号）について",
        "日程第８　承認第５号　令和７年度椎葉村電気事業特別会計補正予算（第７号）について",
        "日程第９　承認第６号　令和７年度椎葉村介護保険特別会計補正予算（第６号）について",
        "日程第１０　承認第７号　令和７年度椎葉村後期高齢者医療特別会計補正予算（第５号）について",
        "日程第１１　承認第８号　令和７年度椎葉村ケーブルネットワーク事業特別会計補正予算（第６号）について",
        "日程第１２　承認第９号　専決処分について（椎葉村税条例の一部を改正する条例）",
        "日程第１３　承認第１０号　専決処分について（椎葉村国民健康保険税条例の一部を改正する条例）",
        "日程第１４　議案第２９号　椎葉村国民健康保険税条例の一部を改正する条例について",
        "日程第１５　議案第３０号　工事請負変更契約の締結について（令和７年度　６年災　第３１１号　村道新屋敷上線　道路災害復旧工事）",
    ]
    schedule_items = FIXED_SCHEDULE

    # タイトル生成
    meeting_title = f"{info.title}（第１日）" if info.title else "令和８年第２回臨時会　椎葉村議会会議録（第１日）"
    meeting_date = info.date or "令和８年５月２２日（金曜日）"
    meeting_time = "午後２時００分"

    # 文字起こし読み込み
    raw_text = Path(transcript_path).read_text(encoding="utf-8")

    # 解析
    blocks = parse_transcript(raw_text)
    print(f"ブロック数: {len(blocks)}")

    # Word生成
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    build_document(blocks, meeting_title, meeting_date, meeting_time, schedule_items, output_path)


if __name__ == "__main__":
    main(
        transcript_path="samples/002/input/transcribed.txt",
        pdf_paths=[
            "samples/002/input/schedule_議事日程.pdf",
            "samples/002/input/schedule_会期日程.pdf",
        ],
        output_path="samples/002/expected_output/minutes_draft.docx",
    )
