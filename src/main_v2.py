#!/usr/bin/env python3
"""汎用議事録生成エントリーポイント"""
import argparse
import sys
from pathlib import Path

# src ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from meeting_config import load_config
from generate_minutes_v2 import generate_minutes_from_notta


def main() -> None:
    parser = argparse.ArgumentParser(description="椎葉村議会 議事録自動生成")
    parser.add_argument("--notta", required=True, help="NottaのTXTファイル")
    parser.add_argument("--config", required=True, help="会議設定YAMLファイル")
    parser.add_argument("--output", required=True, help="出力Wordファイル")
    args = parser.parse_args()

    config = load_config(args.config)
    generate_minutes_from_notta(args.notta, args.output, config)

    from docx import Document
    doc = Document(args.output)
    print(f"\n=== 生成完了: {len(doc.paragraphs)}段落 ===")


if __name__ == "__main__":
    main()
