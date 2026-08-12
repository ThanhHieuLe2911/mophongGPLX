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


if __name__ == "__main__":
    unittest.main()
