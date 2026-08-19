import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from gplx_sim.bootstrap import initialize_databases
from gplx_sim.paths import AppPaths
from gplx_sim.repositories.content_repository import ContentRepository


class RepositoryTests(unittest.TestCase):
    def test_bundled_database_contains_120_complete_situations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gplx_test_") as directory:
            root = Path(directory)
            paths = AppPaths(root, root / "content", root / "runtime")
            initialize_databases(paths)
            repository = ContentRepository(paths.content_database)
            situation = repository.get_situation(1)

            self.assertEqual(repository.count_situations(), 120)
            self.assertEqual(situation.code, "TH001")
            self.assertEqual(situation.video_filename, "1.mp4")
            self.assertEqual(len(situation.parts), 4)
            self.assertTrue(all(len(part.answers) == 4 for part in situation.parts))
            self.assertTrue(
                all(sum(answer.is_correct for answer in part.answers) == 1 for part in situation.parts)
            )
            self.assertTrue(paths.bundled_content_database.is_file())
            self.assertTrue(paths.content_database.is_file())
            self.assertNotEqual(paths.bundled_content_database, paths.content_database)

    def test_restarting_does_not_overwrite_local_content_edits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gplx_test_") as directory:
            root = Path(directory)
            paths = AppPaths(root, root / "content", root / "runtime")
            initialize_databases(paths)
            with closing(sqlite3.connect(paths.content_database)) as connection, connection:
                connection.execute("UPDATE situations SET title = 'Tên đã sửa' WHERE id = 1")

            initialize_databases(paths)
            situation = ContentRepository(paths.content_database).get_situation(1)
            self.assertEqual(situation.title, "Tên đã sửa")

    def test_repository_lists_all_chapters_and_situations_for_custom_practice(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gplx_test_") as directory:
            root = Path(directory)
            paths = AppPaths(root, root / "content", root / "runtime")
            initialize_databases(paths)
            repository = ContentRepository(paths.content_database)

            chapters = repository.list_chapters()
            situations = repository.list_situations()

            self.assertEqual(len(chapters), 6)
            self.assertEqual(len(situations), 120)
            self.assertEqual((situations[0].id, situations[0].code), (1, "TH001"))
            self.assertEqual((situations[-1].id, situations[-1].code), (120, "TH120"))
            selected = repository.get_situations_by_ids([120, 1, 120])
            self.assertEqual([situation.id for situation in selected], [120, 1])

    def test_get_exam_situations_respects_chapter_distribution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gplx_test_") as directory:
            root = Path(directory)
            paths = AppPaths(root, root / "content", root / "runtime")
            initialize_databases(paths)
            repository = ContentRepository(paths.content_database)

            situations = repository.get_exam_situations()

            self.assertEqual(len(situations), 10)
            chapters = [situation.chapter for situation in situations]
            expected_order = [
                "Giao thông khi đi trong khu đô thị, khu dân cư đông đúc",
                "Giao thông khi đi trong khu đô thị, khu dân cư đông đúc",
                "Giao thông trên đường tối, đường gấp khúc, khúc cua",
                "Giao thông khi lái xe trên đường cao tốc",
                "Giao thông khi lái xe trên đường cao tốc",
                "Giao thông trên đường đèo núi, lên dốc, xuống dốc hoặc khúc cua gấp",
                "Giao thông trên quốc lộ, khu vực ngoại thành, giao cắt đường sắt hoặc người đi bộ",
                "Giao thông trên quốc lộ, khu vực ngoại thành, giao cắt đường sắt hoặc người đi bộ",
                "Các tình huống va chạm thực tế khi tham gia giao thông hỗn hợp",
                "Các tình huống va chạm thực tế khi tham gia giao thông hỗn hợp",
            ]
            self.assertEqual(chapters, expected_order)
            self.assertEqual(len({situation.id for situation in situations}), 10)


if __name__ == "__main__":
    unittest.main()
