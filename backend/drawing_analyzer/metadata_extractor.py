from __future__ import annotations

import re


class DrawingMetadataExtractor:
    """Extract only explicit or strongly identifiable metadata from drawing text."""

    _DOCUMENT_CODE = re.compile(
        r"\b[A-Z]{1,8}-\d{2,6}(?:[-_/][A-Z0-9]+)*\b",
        re.IGNORECASE,
    )
    _REVISION = re.compile(
        r"\b(?:revision|rev\.?)\s*[:\-]?\s*([A-Z0-9]+)\b",
        re.IGNORECASE,
    )
    _DATE = re.compile(
        r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"
    )
    _TITLE = re.compile(
        r"^(?:title|titulo|drawing title|nombre del plano)\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    )
    _DISCIPLINES = {
        "civil": re.compile(r"\bcivil\b", re.IGNORECASE),
        "electrical": re.compile(
            r"\b(?:electrical|electrica|electrico)\b",
            re.IGNORECASE,
        ),
        "mechanical": re.compile(
            r"\b(?:mechanical|mecanica|mecanico)\b",
            re.IGNORECASE,
        ),
        "protection": re.compile(r"\b(?:protection|proteccion)\b", re.IGNORECASE),
        "control": re.compile(r"\bcontrol\b", re.IGNORECASE),
        "telecom": re.compile(r"\b(?:telecom|telecommunications)\b", re.IGNORECASE),
    }

    def extract_metadata(self, text: str) -> dict[str, str | None]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        document_match = self._DOCUMENT_CODE.search(text)
        revision_match = self._REVISION.search(text)
        date_match = self._DATE.search(text)

        discipline = next(
            (
                name
                for name, pattern in self._DISCIPLINES.items()
                if pattern.search(text)
            ),
            None,
        )

        return {
            "title": self._extract_title(lines, document_match),
            "document_code": document_match.group(0) if document_match else None,
            "revision": revision_match.group(1) if revision_match else None,
            "date": date_match.group(0) if date_match else None,
            "discipline": discipline,
        }

    def _extract_title(
        self,
        lines: list[str],
        document_match: re.Match[str] | None,
    ) -> str | None:
        for line in lines:
            title_match = self._TITLE.match(line)
            if title_match:
                return title_match.group(1).strip() or None

        if document_match is None:
            return None

        code = document_match.group(0).casefold()
        code_index = next(
            (index for index, line in enumerate(lines) if code in line.casefold()),
            None,
        )
        if code_index is None:
            return None

        for line in lines[code_index + 1 : code_index + 4]:
            if self._is_title_candidate(line):
                return line
        return None

    def _is_title_candidate(self, line: str) -> bool:
        if not any(character.isalpha() for character in line):
            return False
        if self._REVISION.search(line) or self._DATE.search(line):
            return False
        if any(pattern.fullmatch(line) for pattern in self._DISCIPLINES.values()):
            return False
        return len(line) <= 160
