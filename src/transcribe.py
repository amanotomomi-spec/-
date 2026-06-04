"""音声ファイルをWhisperで文字起こしする"""
import whisper
from pathlib import Path


def transcribe(audio_paths: list[str], model_name: str = "large") -> str:
    """複数音声ファイルを結合して文字起こし（順番通りに処理）"""
    model = whisper.load_model(model_name)
    segments_all: list[str] = []

    for path in audio_paths:
        print(f"文字起こし中: {path}")
        result = model.transcribe(
            path,
            language="ja",
            verbose=False,
            initial_prompt=(
                "椎葉村議会の会議録です。議長、議員、村長、課長などが発言します。"
                "固有名詞：岡村正司、椎葉邦博、甲斐美義、那須重美、尾前秀久、"
                "河口吉弘、椎葉一、藏座二九生、椎葉智成、椎葉大和、"
                "黒木保隆、椎葉和博、柚木和浩、甲斐万寿也"
            ),
        )
        text = result["text"].strip()
        segments_all.append(text)

    return "\n".join(segments_all)


if __name__ == "__main__":
    import sys
    paths = sys.argv[1:]
    print(transcribe(paths))
