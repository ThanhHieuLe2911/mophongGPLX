from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSize
from PySide6.QtGui import QImage
from PySide6.QtPdf import QPdfDocument


CHAPTERS = (
    (1, "C1", "Giao thông khi đi trong khu đô thị, khu dân cư đông đúc", 1, 29),
    (2, "C2", "Giao thông trên đường tối, đường gấp khúc, khúc cua", 30, 43),
    (3, "C3", "Giao thông khi lái xe trên đường cao tốc", 44, 63),
    (4, "C4", "Giao thông trên đường đèo núi, lên dốc, xuống dốc hoặc khúc cua gấp", 64, 73),
    (5, "C5", "Giao thông trên quốc lộ, khu vực ngoại thành, giao cắt đường sắt hoặc người đi bộ", 74, 90),
    (6, "C6", "Các tình huống va chạm thực tế khi tham gia giao thông hỗn hợp", 91, 120),
)

PART_KINDS = ("recognition", "indirect", "direct", "handling")
PART_PATTERN = re.compile(r"^([1-4])\.\s*(.+)$")
ANSWER_PATTERN = re.compile(r"^([A-D])\s*\.\s*(.+)$")
SITUATION_PATTERN = re.compile(r"^Tình\s+Huống\s+(\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class TextLine:
    text: str
    start: int
    end: int


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def chapter_id(number: int) -> int:
    for identifier, _code, _name, first, last in CHAPTERS:
        if first <= number <= last:
            return identifier
    raise ValueError(f"Tình huống {number} không thuộc chương nào")


def text_lines(text: str) -> list[TextLine]:
    result: list[TextLine] = []
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        stripped = raw_line.strip()
        if stripped:
            leading = len(raw_line) - len(raw_line.lstrip())
            start = offset + leading
            result.append(TextLine(stripped, start, offset + len(raw_line.rstrip("\r\n"))))
        offset += len(raw_line)
    return result


def contains_red_text(
    document: QPdfDocument,
    rendered: QImage,
    page: int,
    start: int,
    end: int,
    scale: int,
) -> bool:
    selection = document.getSelectionAtIndex(page, start, max(end - start, 1))
    rectangle = selection.boundingRectangle()
    if rectangle.isEmpty():
        return False

    pixels = rendered.constBits()
    stride = rendered.bytesPerLine()
    left = max(0, int(rectangle.left() * scale) - 2)
    right = min(rendered.width(), int(rectangle.right() * scale) + 3)
    top = max(0, int(rectangle.top() * scale) - 2)
    bottom = min(rendered.height(), int(rectangle.bottom() * scale) + 3)

    red_pixels = 0
    for y in range(top, bottom):
        row = y * stride
        for x in range(left, right):
            index = row + x * 4
            red, green, blue = pixels[index], pixels[index + 1], pixels[index + 2]
            if red >= 150 and red > green * 1.45 and red > blue * 1.45:
                red_pixels += 1
                if red_pixels >= 12:
                    return True
    return False


def parse_page(document: QPdfDocument, page: int, scale: int = 2) -> dict:
    all_text = document.getAllText(page).text()
    lines = text_lines(all_text)
    if not lines:
        raise ValueError(f"Trang {page + 1} không có văn bản")

    match = SITUATION_PATTERN.match(lines[0].text)
    if not match:
        raise ValueError(f"Trang {page + 1} không có tiêu đề 'Tình Huống N'")
    number = int(match.group(1))
    if number != page + 1:
        raise ValueError(f"Trang {page + 1} chứa tình huống {number}")

    page_size = document.pagePointSize(page)
    rendered = document.render(
        page,
        QSize(round(page_size.width() * scale), round(page_size.height() * scale)),
    ).convertToFormat(QImage.Format.Format_RGBA8888)

    first_part = next((index for index, line in enumerate(lines) if PART_PATTERN.match(line.text)), None)
    if first_part is None:
        raise ValueError(f"Tình huống {number} không có phần câu hỏi")
    title = normalize(" ".join(line.text for line in lines[1:first_part]))

    parts: list[dict] = []
    index = first_part
    while index < len(lines):
        part_match = PART_PATTERN.match(lines[index].text)
        if not part_match:
            raise ValueError(f"Tình huống {number}: dòng phần không hợp lệ: {lines[index].text}")
        part_number = int(part_match.group(1))
        prompt_fragments = [part_match.group(2)]
        index += 1
        while index < len(lines) and not ANSWER_PATTERN.match(lines[index].text):
            if PART_PATTERN.match(lines[index].text):
                break
            prompt_fragments.append(lines[index].text)
            index += 1

        answers: list[dict] = []
        while index < len(lines):
            if PART_PATTERN.match(lines[index].text):
                break
            answer_match = ANSWER_PATTERN.match(lines[index].text)
            if not answer_match:
                raise ValueError(
                    f"Tình huống {number}, phần {part_number}: thiếu ký hiệu đáp án tại '{lines[index].text}'"
                )
            letter = answer_match.group(1)
            fragments = [answer_match.group(2)]
            start = lines[index].start
            end = lines[index].end
            index += 1
            while index < len(lines):
                if PART_PATTERN.match(lines[index].text) or ANSWER_PATTERN.match(lines[index].text):
                    break
                fragments.append(lines[index].text)
                end = lines[index].end
                index += 1
            answers.append(
                {
                    "label": letter,
                    "text": normalize(" ".join(fragments)),
                    "is_correct": contains_red_text(document, rendered, page, start, end, scale),
                }
            )

        if len(answers) != 4:
            raise ValueError(f"Tình huống {number}, phần {part_number} có {len(answers)} đáp án")
        correct_count = sum(answer["is_correct"] for answer in answers)
        if correct_count != 1:
            raise ValueError(
                f"Tình huống {number}, phần {part_number} nhận diện được {correct_count} đáp án đúng"
            )
        parts.append(
            {
                "kind": PART_KINDS[part_number - 1],
                "prompt": normalize(" ".join(prompt_fragments)),
                "answers": answers,
            }
        )

    if len(parts) != 4:
        raise ValueError(f"Tình huống {number} có {len(parts)} phần câu hỏi")
    if not title:
        title = next(
            answer["text"] for answer in parts[0]["answers"] if answer["is_correct"]
        )
    return {
        "id": number,
        "code": f"TH{number:03d}",
        "chapter_id": chapter_id(number),
        "title": title,
        "video_filename": f"{number}.mp4",
        "active": True,
        "parts": parts,
    }


def import_pdf(pdf_path: Path, output_path: Path) -> None:
    application = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    del application
    document = QPdfDocument(None)
    error = document.load(str(pdf_path))
    if error != QPdfDocument.Error.None_:
        raise OSError(f"Không mở được PDF: {error}")
    if document.pageCount() != 120:
        raise ValueError(f"MP1.pdf phải có 120 trang, hiện có {document.pageCount()}")

    situations = []
    for page in range(document.pageCount()):
        situations.append(parse_page(document, page))
        print(f"Đã đọc {page + 1:03d}/120", end="\r", flush=True)
    print()

    catalog = {
        "schema_version": 1,
        "content_version": "2026.08.12",
        "chapters": [
            {"id": identifier, "code": code, "name": name, "first": first, "last": last}
            for identifier, code, name, first, last in CHAPTERS
        ],
        "situations": situations,
        "practice_sets": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Đã tạo {output_path} với {len(situations)} tình huống")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trích 120 tình huống và đáp án đỏ từ MP1.pdf")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    import_pdf(arguments.pdf.resolve(), arguments.output.resolve())


if __name__ == "__main__":
    main()
