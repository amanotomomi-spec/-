"""
会議設定をYAMLファイルから読み込むデータクラスとローダー。
"""
from dataclasses import dataclass, field
import yaml
from pathlib import Path


@dataclass
class MeetingConfig:
    # 会議基本情報
    title: str
    date: str
    open_time: str

    # 議事日程
    agenda_items: list[str]

    # 出席者
    attending_count: int
    attending_members: list[str]
    absent_members: list[str]
    seat_members: list[str]
    absent_seat: list[str]
    clerk_staff: list[str]
    explain_staff: list[str]

    # 発言者マッピング (role_key -> 正式表記)
    speakers: dict[str, str]

    # 会議固有の誤変換補正 (wrong -> correct)
    extra_corrections: list[tuple[str, str]] = field(default_factory=list)


def load_config(path: str) -> MeetingConfig:
    """YAMLファイルからMeetingConfigを読み込む。"""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    meeting = data["meeting"]
    members = data["members"]

    extra_corrections: list[tuple[str, str]] = []
    for item in data.get("extra_corrections", []):
        if isinstance(item, dict):
            wrong = item.get("wrong", "")
            correct = item.get("correct", "")
            extra_corrections.append((wrong, correct))
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            extra_corrections.append((item[0], item[1]))

    speakers: dict[str, str] = data.get("speakers", {})

    return MeetingConfig(
        title=meeting["title"],
        date=meeting["date"],
        open_time=meeting["open_time"],
        agenda_items=data.get("agenda_items", []),
        attending_count=members.get("attending_count", 0),
        attending_members=members.get("attending", []),
        absent_members=members.get("absent", []),
        seat_members=members.get("seats", []),
        absent_seat=members.get("absent_seats", []),
        clerk_staff=members.get("clerk", []),
        explain_staff=members.get("explain", []),
        speakers=speakers,
        extra_corrections=extra_corrections,
    )
