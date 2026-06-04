"""会議日程PDFから構造データを抽出する"""
import re
import subprocess
from dataclasses import dataclass, field


@dataclass
class ScheduleItem:
    number: int
    title: str


@dataclass
class MeetingInfo:
    title: str = ""
    date: str = ""
    time: str = ""
    items: list[ScheduleItem] = field(default_factory=list)
    members_present: list[str] = field(default_factory=list)
    members_absent: list[str] = field(default_factory=list)
    proper_nouns: list[str] = field(default_factory=list)


def extract_text(pdf_path: str) -> str:
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True
    )
    return result.stdout


def parse_schedule(pdf_paths: list[str]) -> MeetingInfo:
    info = MeetingInfo()
    full_text = "\n".join(extract_text(p) for p in pdf_paths)

    # 会議名
    m = re.search(r"(令和\d+年\s*椎葉村議会\s*第\d+回\S+会)", full_text)
    if m:
        info.title = m.group(1).replace("\n", "").replace(" ", "　")

    # 日付
    m = re.search(r"(令和\d+年\d+月\d+日[（(][^）)]+[）)])", full_text)
    if m:
        info.date = m.group(1)

    # 開議時刻
    m = re.search(r"午[前後]\s*(\d+)\s*時\s*(\d*)\s*分?\s*開議", full_text)
    if m:
        hour = m.group(1)
        minute = m.group(2) or "00"
        ampm = "午後" if "午後" in full_text[max(0, m.start()-5):m.start()+10] else "午前"
        info.time = f"{ampm}{hour}時{minute}分"

    # 議事日程
    for m in re.finditer(r"日程第\s*(\d+)\s+(.*?)(?=日程第\s*\d|\Z)", full_text, re.DOTALL):
        num = int(m.group(1))
        raw = m.group(2).strip()
        # 複数行をまとめて1行にする（提案理由説明・質疑等の補足行は除く）
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        # 「提案理由説明」「質疑・討論・採決」「一括上程」などの補足行を除去
        content_lines = [l for l in lines if not re.match(r"(提案理由説明|質疑[・.討論採決]+|一括上程|[①②③\d]+\))", l)]
        title = re.sub(r"\s+", "", " ".join(content_lines))
        if title:
            info.items.append(ScheduleItem(number=num, title=title))

    # 固有名詞（氏名）抽出 - 「君」の前後パターン
    names = re.findall(r"([^\s　（(]{2,6})\s*君", full_text)
    info.proper_nouns = sorted(set(names))

    return info
