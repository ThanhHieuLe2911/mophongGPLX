"""
Build bundled_content.db from content_catalog.json.

Usage:
    python scripts/build_content_db.py

Output:
    content/bundled_content.db

This script is standalone and can be run on any machine with Python 3.10+.
No need for virtualenv or project dependencies.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "src" / "gplx_sim" / "data" / "content_catalog.json"
OUTPUT_PATH = PROJECT_ROOT / "content" / "bundled_content.db"

EXPECTED_CHAPTER_COUNTS = {1: 29, 2: 14, 3: 20, 4: 10, 5: 17, 6: 30}

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS content_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS situations (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    title TEXT NOT NULL,
    video_filename TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS question_parts (
    id INTEGER PRIMARY KEY,
    situation_id INTEGER NOT NULL REFERENCES situations(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    prompt TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    UNIQUE (situation_id, kind)
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY,
    question_part_id INTEGER NOT NULL REFERENCES question_parts(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    display_order INTEGER NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def catalog_checksum(catalog: dict) -> str:
    """Compute SHA-256 of the canonical JSON for the catalog."""
    canonical = json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_catalog(catalog: dict) -> None:
    """Validate that the catalog has the expected structure."""
    chapters = catalog.get("chapters", [])
    situations = catalog.get("situations", [])

    if len(chapters) != 6:
        raise ValueError(f"Catalog phai co 6 chuong, hien co {len(chapters)}")
    if len(situations) != 120:
        raise ValueError(f"Catalog phai co 120 tinh huong, hien co {len(situations)}")

    identifiers = [int(s["id"]) for s in situations]
    if identifiers != list(range(1, 121)):
        raise ValueError("Tinh huong phai duoc sap dung thu tu tu 1 den 120")

    chapter_counts = {chapter_id: 0 for chapter_id in EXPECTED_CHAPTER_COUNTS}
    for situation in situations:
        identifier = int(situation["id"])
        expected_code = f"TH{identifier:03d}"
        expected_video = f"{identifier}.mp4"

        if situation["code"] != expected_code:
            raise ValueError(f"Tinh huong {identifier} phai co ma {expected_code}")
        if situation["video_filename"] != expected_video:
            raise ValueError(f"Tinh huong {identifier} phai dung video {expected_video}")
        if not str(situation["title"]).strip():
            raise ValueError(f"Tinh huong {identifier} chua co ten")

        chapter_id = int(situation["chapter_id"])
        if chapter_id not in chapter_counts:
            raise ValueError(f"Tinh huong {identifier} co chuong khong hop le")
        chapter_counts[chapter_id] += 1

        parts = situation.get("parts", [])
        if len(parts) != 4:
            raise ValueError(f"Tinh huong {identifier} phai co dung 4 phan")
        for part_number, part in enumerate(parts, start=1):
            answers = part.get("answers", [])
            if len(answers) != 4:
                raise ValueError(
                    f"Tinh huong {identifier}, phan {part_number} phai co dung 4 phuong an"
                )
            if sum(bool(answer["is_correct"]) for answer in answers) != 1:
                raise ValueError(
                    f"Tinh huong {identifier}, phan {part_number} phai co dung 1 dap an dung"
                )

    if chapter_counts != EXPECTED_CHAPTER_COUNTS:
        raise ValueError(f"So tinh huong theo chuong khong dung: {chapter_counts}")


# ---------------------------------------------------------------------------
# Database building
# ---------------------------------------------------------------------------

def build_database(catalog: dict, destination: Path) -> None:
    """Build the database and write directly to destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Use temp file in same directory for atomic replace
    file_descriptor, tmp_path_str = tempfile.mkstemp(
        prefix=".", suffix=".tmp", dir=destination.parent
    )
    os.close(file_descriptor)
    tmp_path = Path(tmp_path_str)

    try:
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)

        # Metadata
        conn.executemany(
            "INSERT INTO content_metadata(key, value) VALUES (?, ?)",
            (
                ("schema_version", str(catalog["schema_version"])),
                ("content_version", str(catalog["content_version"])),
                ("catalog_sha256", catalog_checksum(catalog)),
                ("situation_count", "120"),
            ),
        )

        # Chapters
        conn.executemany(
            "INSERT INTO chapters(id, code, name) VALUES (?, ?, ?)",
            [(c["id"], c["code"], c["name"]) for c in catalog["chapters"]],
        )

        # Situations, parts, answers
        part_id = 1
        answer_id = 1
        for situation in catalog["situations"]:
            conn.execute(
                """
                INSERT INTO situations (id, code, chapter_id, title, video_filename, active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    situation["id"],
                    situation["code"],
                    situation["chapter_id"],
                    situation["title"],
                    situation["video_filename"],
                    int(situation.get("active", True)),
                ),
            )
            for part_order, part in enumerate(situation["parts"], start=1):
                conn.execute(
                    """
                    INSERT INTO question_parts (id, situation_id, kind, prompt, display_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (part_id, situation["id"], part["kind"], part["prompt"], part_order),
                )
                for answer_order, answer in enumerate(part["answers"], start=1):
                    conn.execute(
                        """
                        INSERT INTO answers
                            (id, question_part_id, answer_text, is_correct, display_order)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            answer_id,
                            part_id,
                            answer["text"],
                            int(answer["is_correct"]),
                            answer_order,
                        ),
                    )
                    answer_id += 1
                part_id += 1

        conn.execute("ANALYZE")
        conn.execute("PRAGMA optimize")
        conn.commit()
        conn.close()

        # Atomic replace
        os.replace(tmp_path, destination)

    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Validation of built database
# ---------------------------------------------------------------------------

def validate_database(db_path: Path) -> None:
    """Validate the built database structure."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Quick integrity check
        quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
        if quick_check != "ok":
            raise ValueError(f"SQLite quick_check that bai: {quick_check}")

        # Count checks
        counts = {
            "chapters": conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0],
            "situations": conn.execute("SELECT COUNT(*) FROM situations").fetchone()[0],
            "question_parts": conn.execute("SELECT COUNT(*) FROM question_parts").fetchone()[0],
            "answers": conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0],
        }
        expected = {"chapters": 6, "situations": 120, "question_parts": 480, "answers": 1920}
        if counts != expected:
            raise ValueError(f"So luong ban ghi khong hop le: {counts}")

        # Answer validity check
        invalid_parts = conn.execute(
            """
            SELECT qp.id
            FROM question_parts qp
            LEFT JOIN answers a ON a.question_part_id = qp.id
            GROUP BY qp.id
            HAVING COUNT(a.id) != 4 OR SUM(a.is_correct) != 1
            LIMIT 1
            """
        ).fetchone()
        if invalid_parts is not None:
            raise ValueError(f"Phan cau hoi {invalid_parts['id']} co dap an khong hop le")

        # Foreign key check
        foreign_key_error = conn.execute("PRAGMA foreign_key_check").fetchone()
        if foreign_key_error is not None:
            raise ValueError("Database co lien ket khoa ngoai khong hop le")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Bat dau build bundled_content.db...")
    print()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"Loi: Can Python 3.10+. Hien tai: {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)

    # Check catalog file exists
    if not CATALOG_PATH.exists():
        print(f"Loi: Khong tim thay file catalog: {CATALOG_PATH}")
        sys.exit(1)

    # Read and validate catalog
    print(f"Doc catalog: {CATALOG_PATH}")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)
    print(f"  - Schema version: {catalog.get('schema_version')}")
    print(f"  - Content version: {catalog.get('content_version')}")
    print(f"  - Chuong: {len(catalog.get('chapters', []))}")
    print(f"  - Tinh huong: {len(catalog.get('situations', []))}")

    print()
    print("Kiem tra tinh hop le cua catalog...")
    try:
        validate_catalog(catalog)
        print("  [OK] Catalog hop le")
    except ValueError as e:
        print(f"  [LOI] {e}")
        sys.exit(1)

    # Build database
    print()
    print("Dang tao database...")
    build_database(catalog, OUTPUT_PATH)
    db_size = OUTPUT_PATH.stat().st_size
    print(f"  - Kich thuoc: {db_size:,} bytes")

    # Validate database
    print()
    print("Kiem tra database...")
    try:
        validate_database(OUTPUT_PATH)
        print("  [OK] Database hop le")
        print("    - 6 chuong")
        print("    - 120 tinh huong")
        print("    - 480 phan cau hoi")
        print("    - 1920 dap an")
    except ValueError as e:
        print(f"  [LOI] {e}")
        sys.exit(1)

    # Compute checksum
    checksum = hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest()

    print()
    print("=" * 60)
    print(f"Da tao thanh cong: {OUTPUT_PATH}")
    print(f"SHA-256: {checksum}")
    print("=" * 60)
    print()
    print("Huong dan su dung:")
    print("  1. Chay script nay sau khi pull code moi")
    print("  2. File bundled_content.db se duoc tao trong thu muc content/")
    print("  3. Khi dong goi app (build.ps1), file nay se tu dong")
    print("     duoc bao gom trong installer")


if __name__ == "__main__":
    main()
