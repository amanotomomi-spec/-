"""
Gem指示書のフォーマットルールを自動チェックするテスト。

チェック対象ルール:
1. 発言行が `〇役職（氏名君）　内容`（全角スペース1つ）形式か
2. 人が変わるとき空行（2連続改行）がないか
3. 同一人物の発言内改行後に全角スペースがあるか
4. 発言内容に半角英数字が含まれていないか（数字・記号は全角のみ）
5. 傍聴発言が `（「...」と呼ぶ者あり）` 形式か
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _extract_paragraphs(path: str) -> list[str]:
    """docx ファイルから段落テキストのリストを返す。"""
    from docx import Document  # type: ignore[import]

    doc = Document(path)
    return [p.text for p in doc.paragraphs]


def check_format(path: str) -> list[str]:
    """
    Gem指示書のフォーマットルールに従い、違反箇所をリストで返す。

    Parameters
    ----------
    path:
        チェック対象の .docx ファイルパス。

    Returns
    -------
    list[str]
        違反の説明文リスト。空リストなら問題なし。
    """
    paragraphs = _extract_paragraphs(path)
    violations: list[str] = []

    # 発言行を判定する正規表現
    # 先頭が〇または○、役職名、（氏名君）、全角スペース1つ、発言内容
    speech_line_pattern = re.compile(
        r"^[〇○].+（.+君）　.+"
    )
    # 発言行の開始を示すパターン（内容がなくてもよい）
    speech_start_pattern = re.compile(r"^[〇○].+（.+君）")

    # 傍聴発言パターン
    bystander_pattern = re.compile(r"^（「.+」と呼ぶ者あり）$")
    # 起立・着席などの傍聴行為パターンも許容
    bystander_action_pattern = re.compile(r"^（.+）$")

    # 半角英数字・半角記号（スペース除く）
    halfwidth_pattern = re.compile(r"[A-Za-z0-9!-/:-@\[-`{-~]")

    prev_is_speech = False
    prev_is_empty = False

    for i, para in enumerate(paragraphs):
        line_num = i + 1
        stripped = para.strip()

        if not stripped:
            # 空行
            if prev_is_empty:
                violations.append(
                    f"行{line_num}: 連続空行が存在します（人が変わるとき空行は1つまで）。"
                )
            prev_is_empty = True
            prev_is_speech = False
            continue

        is_speech = bool(speech_start_pattern.match(stripped))

        # ルール1: 発言行フォーマットチェック
        if is_speech:
            if not speech_line_pattern.match(stripped):
                # 内容なし、または全角スペースがない
                if "　" not in stripped:
                    violations.append(
                        f"行{line_num}: 発言行の役職（氏名君）の後に全角スペースがありません。"
                        f" → {stripped[:40]!r}"
                    )
                elif stripped.endswith("）"):
                    violations.append(
                        f"行{line_num}: 発言行に発言内容がありません。"
                        f" → {stripped[:40]!r}"
                    )

        # ルール2: 人が変わるとき空行（2連続改行）がないか
        # Word上では段落が分かれているため、前後の空段落を検出する
        if prev_is_speech and is_speech and prev_is_empty:
            # 前発言 → 空行 → 次発言 は OK（空行1つ）
            pass  # 上のprev_is_emptyチェックで連続空行は既に検出済み

        # ルール3: 同一人物の発言内改行後（段落が続く場合）に全角スペースがあるか
        # docx では段落が別れているので、前段落が発言行でない通常段落かチェック
        if not is_speech and not stripped.startswith("（") and prev_is_speech is False:
            # 発言の続き（段落継続）として扱う
            if stripped and not stripped.startswith("　"):
                # 先頭に全角スペースがない継続行
                # 傍聴発言・日程見出し・時刻行などは除外
                if not re.match(r"^[午前午後日程〇○（]", stripped) and not re.match(r"^\d", stripped):
                    violations.append(
                        f"行{line_num}: 発言内継続行の先頭に全角スペースがありません。"
                        f" → {stripped[:40]!r}"
                    )

        # ルール4: 発言内容に半角英数字が含まれていないか
        if is_speech:
            # 発言内容部分だけ抽出（全角スペース以降）
            parts = stripped.split("　", 1)
            content = parts[1] if len(parts) > 1 else ""
            if halfwidth_pattern.search(content):
                violations.append(
                    f"行{line_num}: 発言内容に半角英数字または半角記号が含まれています。"
                    f" → {content[:40]!r}"
                )
        elif not is_speech and stripped:
            # 発言継続行や地の文
            if not stripped.startswith("（"):
                if halfwidth_pattern.search(stripped):
                    violations.append(
                        f"行{line_num}: 本文に半角英数字または半角記号が含まれています。"
                        f" → {stripped[:40]!r}"
                    )

        # ルール5: 傍聴発言が正しい形式か
        if stripped.startswith("（") and not stripped.startswith("（「") and not re.match(r"^（賛成者|（全員起立|（起立", stripped):
            # 「と呼ぶ者あり」を含む行は正しい形式かチェック
            if "と呼ぶ者あり" in stripped:
                if not bystander_pattern.match(stripped):
                    violations.append(
                        f"行{line_num}: 傍聴発言の形式が正しくありません。"
                        f"正しくは（「...」と呼ぶ者あり）形式。 → {stripped[:40]!r}"
                    )

        prev_is_empty = False
        prev_is_speech = is_speech

    return violations


# ---------------------------------------------------------------------------
# pytest テスト
# ---------------------------------------------------------------------------

SAMPLE_DOCX = Path(__file__).parent.parent / "samples" / "001" / "expected_output" / "minutes.docx"


@pytest.fixture()
def sample_docx_path() -> str:
    return str(SAMPLE_DOCX)


@pytest.mark.skipif(not SAMPLE_DOCX.exists(), reason="サンプルdocxが存在しない")
def test_check_format_returns_list(sample_docx_path: str) -> None:
    """check_format が list を返すことを確認する。"""
    result = check_format(sample_docx_path)
    assert isinstance(result, list), "check_format はリストを返す必要があります"


@pytest.mark.skipif(not SAMPLE_DOCX.exists(), reason="サンプルdocxが存在しない")
def test_no_halfwidth_in_speech(sample_docx_path: str) -> None:
    """発言内容に半角英数字が含まれていないことを確認する。"""
    violations = check_format(sample_docx_path)
    halfwidth_violations = [v for v in violations if "半角" in v]
    assert halfwidth_violations == [], (
        f"半角文字違反が検出されました:\n" + "\n".join(halfwidth_violations)
    )


@pytest.mark.skipif(not SAMPLE_DOCX.exists(), reason="サンプルdocxが存在しない")
def test_no_double_blank_lines(sample_docx_path: str) -> None:
    """連続空行がないことを確認する。"""
    violations = check_format(sample_docx_path)
    blank_violations = [v for v in violations if "連続空行" in v]
    assert blank_violations == [], (
        f"連続空行違反が検出されました:\n" + "\n".join(blank_violations)
    )


@pytest.mark.skipif(not SAMPLE_DOCX.exists(), reason="サンプルdocxが存在しない")
def test_speech_line_format(sample_docx_path: str) -> None:
    """発言行が正しいフォーマットであることを確認する。"""
    violations = check_format(sample_docx_path)
    format_violations = [v for v in violations if "全角スペース" in v and "役職" in v]
    assert format_violations == [], (
        f"発言行フォーマット違反が検出されました:\n" + "\n".join(format_violations)
    )


@pytest.mark.skipif(not SAMPLE_DOCX.exists(), reason="サンプルdocxが存在しない")
def test_bystander_format(sample_docx_path: str) -> None:
    """傍聴発言が正しい形式であることを確認する。"""
    violations = check_format(sample_docx_path)
    bystander_violations = [v for v in violations if "傍聴発言" in v]
    assert bystander_violations == [], (
        f"傍聴発言フォーマット違反が検出されました:\n" + "\n".join(bystander_violations)
    )


@pytest.mark.skipif(not SAMPLE_DOCX.exists(), reason="サンプルdocxが存在しない")
def test_continuation_line_has_fullwidth_space(sample_docx_path: str) -> None:
    """発言継続行の先頭に全角スペースがあることを確認する。"""
    violations = check_format(sample_docx_path)
    continuation_violations = [v for v in violations if "継続行" in v]
    assert continuation_violations == [], (
        f"継続行フォーマット違反が検出されました:\n" + "\n".join(continuation_violations)
    )


# ---------------------------------------------------------------------------
# インライン単体テスト（モックdocxを使わずロジックをテスト）
# ---------------------------------------------------------------------------

def test_check_format_with_nonexistent_file() -> None:
    """存在しないファイルを渡したとき例外が発生することを確認する。"""
    with pytest.raises(Exception):
        check_format("/nonexistent/path/to/file.docx")


def test_halfwidth_detection_logic() -> None:
    """半角検出ロジックの単体テスト（正規表現）。"""
    import re
    halfwidth_pattern = re.compile(r"[A-Za-z0-9!-/:-@\[-`{-~]")
    assert halfwidth_pattern.search("ＡＢＣ１２３") is None, "全角は検出しない"
    assert halfwidth_pattern.search("ABC123") is not None, "半角は検出する"
    assert halfwidth_pattern.search("１億５，３８３万") is None, "全角数字・記号は検出しない"


def test_bystander_pattern_logic() -> None:
    """傍聴発言パターンの単体テスト。"""
    import re
    pattern = re.compile(r"^（「.+」と呼ぶ者あり）$")
    assert pattern.match("（「異議なし」と呼ぶ者あり）") is not None
    assert pattern.match("（「賛成討論なし」と呼ぶ者あり）") is not None
    assert pattern.match("（異議なしと呼ぶ者あり）") is None
    assert pattern.match("（「異議なし」と呼ぶ者あり）追記") is None
