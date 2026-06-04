"""議事録自動生成メインスクリプト"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from transcribe import transcribe
from parse_pdf import parse_schedule
from generate_minutes import generate_word


def main() -> None:
    parser = argparse.ArgumentParser(description="椎葉村議会 議事録自動生成")
    parser.add_argument("--audio", nargs="+", required=True, help="音声ファイル（複数可、順番通りに指定）")
    parser.add_argument("--pdf", nargs="+", required=True, help="会議日程PDFファイル（複数可）")
    parser.add_argument("--output", default="output/minutes.docx", help="出力Wordファイルパス")
    parser.add_argument("--model", default="large", help="Whisperモデル (tiny/base/small/medium/large)")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print("=== 1. 会議日程PDF解析 ===")
    meeting_info = parse_schedule(args.pdf)
    print(f"会議名: {meeting_info.title}")
    print(f"日付: {meeting_info.date}")
    print(f"日程: {len(meeting_info.items)}件")
    print(f"固有名詞: {meeting_info.proper_nouns}")

    print("\n=== 2. 音声文字起こし ===")
    transcribed = transcribe(args.audio, model_name=args.model)
    print(f"文字起こし完了: {len(transcribed)}文字")

    # 中間ファイル保存
    txt_path = Path(args.output).with_suffix(".txt")
    txt_path.write_text(transcribed, encoding="utf-8")
    print(f"文字起こし保存: {txt_path}")

    print("\n=== 3. Word生成 ===")
    generate_word(transcribed, meeting_info, args.output)
    print("完了!")


if __name__ == "__main__":
    main()
