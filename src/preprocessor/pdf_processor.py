"""PDF ドキュメントプロセッサ."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.common.models import PreprocessingResult
from src.preprocessor.base import DocumentPreprocessor
from src.preprocessor.text_normalizer import JapaneseTextNormalizer

logger = logging.getLogger(__name__)


class PDFProcessor(DocumentPreprocessor):
    """PDF ファイルのテキスト抽出と前処理。"""

    SUPPORTED_FORMATS = {"pdf"}

    def __init__(self, normalizer: JapaneseTextNormalizer | None = None):
        self.normalizer = normalizer or JapaneseTextNormalizer()

    def process(self, file_path: str | Path) -> PreprocessingResult:
        """PDF からテキストを抽出し構造化。"""
        file_path = Path(file_path)

        if not file_path.exists():
            return PreprocessingResult(error=f"ファイルが見つかりません: {file_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError:
            return PreprocessingResult(error="PyMuPDF がインストールされていません (pip install PyMuPDF)")

        try:
            doc = fitz.open(str(file_path))
            pages_text = []
            tables = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                pages_text.append(text)

                # 表の検出（PyMuPDFの表抽出機能を使用）
                try:
                    page_tables = page.find_tables()
                    for tab in page_tables:
                        if tab.extract():
                            tables.append({
                                "page": page_num + 1,
                                "data": tab.extract(),
                            })
                except Exception:
                    pass

            doc.close()

            raw_text = "\n\n".join(pages_text)
            normalized_text = self.normalizer.normalize(raw_text)

            structured = self._build_structured_text(normalized_text, tables)

            return PreprocessingResult(
                raw_text=raw_text,
                structured_text=structured,
                metadata={
                    "filename": file_path.name,
                    "pages": len(doc) if hasattr(doc, '__len__') else len(pages_text),
                    "tables_found": len(tables),
                },
                pages=pages_text,
                tables=tables,
            )

        except Exception as e:
            logger.exception(f"PDF processing failed: {file_path}")
            return PreprocessingResult(error=f"PDF処理エラー: {e}")

    def detect_encoding(self, file_path: str | Path) -> str:
        return "utf-8"  # PDF は内部でエンコーディング管理

    def _build_structured_text(
        self, text: str, tables: list[dict[str, Any]]
    ) -> str:
        """表情報を埋め込んだ構造化テキストを構築。"""
        lines = text.split("\n")

        # 見出しレベルを推定（フォントサイズが取得できないためルールベース）
        structured_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 【】で囲まれた見出し
            if stripped.startswith("【") and stripped.endswith("】"):
                structured_lines.append(f"\n## {stripped}\n")
            # ■ や ● で始まる見出し
            elif stripped.startswith(("■", "●", "・")):
                structured_lines.append(f"\n### {stripped}")
            else:
                structured_lines.append(stripped)

        text = "\n".join(structured_lines)

        # 表情報を末尾に追加
        for idx, table in enumerate(tables):
            text += f"\n\n[TABLE {idx + 1}]\n"
            for row in table["data"]:
                text += " | ".join(str(cell or "") for cell in row) + "\n"
            text += "[/TABLE]\n"

        return text
