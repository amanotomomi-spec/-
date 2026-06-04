"""
固有名詞チェックテスト。

- pdfplumber で schedule.pdf から議員名・役職名を抽出
- docx の発言行の氏名が PDF 抽出リストに含まれているか確認
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def extract_names_from_pdf(pdf_path: str) -> list[str]:
    """
    schedule.pdf から議員名・役職名を抽出して返す。

    Parameters
    ----------
    pdf_path:
        スケジュールPDFのファイルパス。

    Returns
    -------
    list[str]
        抽出された氏名リスト（重複なし）。
        例: ["岡村　正司", "甲斐　万寿也", ...]
    """
    import pdfplumber  # type: ignore[import]

    names: list[str] = []
    # 氏名パターン: 姓と名の間に全角スペース、末尾に「君」が付くことが多い
    name_pattern = re.compile(r"([^\s（）、。\n]{1,5}　[^\s（）、。\n]{1,5})(?:君)?")

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for match in name_pattern.finditer(text):
                candidate = match.group(1).strip()
                # 短すぎるものや明らかに氏名でないものを除外
                if len(candidate) >= 3 and "　" in candidate:
                    if candidate not in names:
                        names.append(candidate)

    return names


def _extract_speech_names_from_docx(docx_path: str) -> list[tuple[int, str]]:
    """
    docx の発言行から氏名を抽出する。

    Returns
    -------
    list[tuple[int, str]]
        (段落番号, 氏名) のリスト。
    """
    from docx import Document  # type: ignore[import]

    doc = Document(docx_path)
    # 発言行パターン: 〇役職（氏名君）　内容
    speech_pattern = re.compile(r"^[〇○].+?（(.+?)君）")
    results: list[tuple[int, str]] = []

    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        match = speech_pattern.match(text)
        if match:
            raw_name = match.group(1).strip()
            # 番号付き議員名（例: ２番　藏座　二九生）の場合、氏名部分だけ抽出
            # 「N番　氏名」形式
            num_pattern = re.compile(r"^\d+番\s*(.+)$")
            num_match = num_pattern.match(raw_name)
            if num_match:
                raw_name = num_match.group(1).strip()
            # 全角番号「２番　氏名」形式
            znum_pattern = re.compile(r"^[０-９]+番\s*(.+)$")
            znum_match = znum_pattern.match(raw_name)
            if znum_match:
                raw_name = znum_match.group(1).strip()
            results.append((i + 1, raw_name))

    return results


def check_proper_nouns(docx_path: str, names: list[str]) -> list[str]:
    """
    docx の発言行の氏名が PDF 抽出リストに含まれているか確認する。

    Parameters
    ----------
    docx_path:
        チェック対象の .docx ファイルパス。
    names:
        PDFから抽出した正規の氏名リスト。

    Returns
    -------
    list[str]
        違反の説明文リスト（正規リストにない氏名が含まれている行）。
        空リストなら問題なし。
    """
    speech_names = _extract_speech_names_from_docx(docx_path)
    violations: list[str] = []

    for line_num, name in speech_names:
        # 完全一致でチェック
        if name not in names:
            # 部分一致でも試みる（PDF抽出が不完全な場合の緩い照合）
            partial_match = any(name in n or n in name for n in names)
            if not partial_match:
                violations.append(
                    f"行{line_num}: 氏名 {name!r} がPDF抽出リストに見つかりません。"
                )

    return violations


# ---------------------------------------------------------------------------
# pytest テスト
# ---------------------------------------------------------------------------

SAMPLE_PDF = Path(__file__).parent.parent / "samples" / "001" / "input" / "schedule.pdf"
SAMPLE_DOCX = Path(__file__).parent.parent / "samples" / "001" / "expected_output" / "minutes.docx"


@pytest.fixture()
def sample_pdf_path() -> str:
    return str(SAMPLE_PDF)


@pytest.fixture()
def sample_docx_path() -> str:
    return str(SAMPLE_DOCX)


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="サンプルPDFが存在しない")
def test_extract_names_from_pdf_returns_list(sample_pdf_path: str) -> None:
    """extract_names_from_pdf がリストを返すことを確認する。"""
    result = extract_names_from_pdf(sample_pdf_path)
    assert isinstance(result, list), "extract_names_from_pdf はリストを返す必要があります"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="サンプルPDFが存在しない")
def test_extract_names_from_pdf_not_empty(sample_pdf_path: str) -> None:
    """PDFから1件以上の氏名が抽出できることを確認する。"""
    result = extract_names_from_pdf(sample_pdf_path)
    assert len(result) > 0, "PDFから氏名を1件以上抽出できる必要があります"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="サンプルPDFが存在しない")
def test_extracted_names_contain_fullwidth_space(sample_pdf_path: str) -> None:
    """抽出された氏名が全角スペースを含むことを確認する。"""
    result = extract_names_from_pdf(sample_pdf_path)
    for name in result:
        assert "　" in name, f"氏名 {name!r} に全角スペースが含まれていません"


@pytest.mark.skipif(
    not SAMPLE_PDF.exists() or not SAMPLE_DOCX.exists(),
    reason="サンプルファイルが存在しない",
)
def test_check_proper_nouns_returns_list(
    sample_docx_path: str, sample_pdf_path: str
) -> None:
    """check_proper_nouns がリストを返すことを確認する。"""
    names = extract_names_from_pdf(sample_pdf_path)
    result = check_proper_nouns(sample_docx_path, names)
    assert isinstance(result, list), "check_proper_nouns はリストを返す必要があります"


@pytest.mark.skipif(
    not SAMPLE_PDF.exists() or not SAMPLE_DOCX.exists(),
    reason="サンプルファイルが存在しない",
)
def test_proper_nouns_in_docx_match_pdf(
    sample_docx_path: str, sample_pdf_path: str
) -> None:
    """docxの発言行の氏名がPDF抽出リストと整合することを確認する。"""
    names = extract_names_from_pdf(sample_pdf_path)
    violations = check_proper_nouns(sample_docx_path, names)
    assert violations == [], (
        f"固有名詞の不一致が検出されました:\n" + "\n".join(violations)
    )


def test_check_proper_nouns_with_empty_names() -> None:
    """空の氏名リストを渡したとき、存在しないファイルなら例外が出ることを確認する。"""
    with pytest.raises(Exception):
        check_proper_nouns("/nonexistent/file.docx", [])


def test_extract_names_logic() -> None:
    """氏名パターンの正規表現ロジック単体テスト。"""
    pattern = re.compile(r"([^\s（）、。\n]{1,5}　[^\s（）、。\n]{1,5})(?:君)?")
    text = "岡村　正司君　議長として出席\n甲斐　万寿也君　事務局長"
    matches = [m.group(1) for m in pattern.finditer(text)]
    assert "岡村　正司" in matches
    assert "甲斐　万寿也" in matches
