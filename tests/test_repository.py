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

    def test_repository_loads_admin_practice_set_in_configured_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gplx_test_") as directory:
            root = Path(directory)
            paths = AppPaths(root, root / "content", root / "runtime")
            initialize_databases(paths)
            with closing(sqlite3.connect(paths.content_database)) as connection, connection:
                connection.execute(
                    "INSERT INTO practice_sets(id, code, name, active) VALUES (1, 'BD01', 'Bộ đề 01', 1)"
                )
                connection.executemany(
                    """
                    INSERT INTO practice_set_items(practice_set_id, situation_id, display_order)
                    VALUES (1, ?, ?)
                    """,
                    [(7, 1), (3, 2), (12, 3)],
                )

            repository = ContentRepository(paths.content_database)
            practice_sets = repository.list_practice_sets()
            situations = repository.get_practice_set_situations(1)

            self.assertEqual(len(practice_sets), 1)
            self.assertEqual(practice_sets[0].situation_count, 3)
            self.assertEqual([situation.id for situation in situations], [7, 3, 12])


if __name__ == "__main__":
    unittest.main()
