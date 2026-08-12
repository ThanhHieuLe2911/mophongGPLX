import tempfile
import unittest
from pathlib import Path

from gplx_sim.bootstrap import initialize_databases
from gplx_sim.paths import AppPaths
from gplx_sim.repositories.content_repository import ContentRepository


class RepositoryTests(unittest.TestCase):
    def test_demo_database_contains_complete_situation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gplx_test_") as directory:
            root = Path(directory)
            paths = AppPaths(root, root / "content", root / "runtime")
            initialize_databases(paths)
            repository = ContentRepository(paths.content_database)
            situations = repository.get_random_situations(1, 3)

            self.assertEqual(len(situations), 1)
            self.assertEqual(situations[0].code, "TH001")
            self.assertEqual(len(situations[0].parts), 4)
            self.assertTrue(all(len(part.answers) == 3 for part in situations[0].parts))
            self.assertTrue(
                all(sum(answer.is_correct for answer in part.answers) == 1 for part in situations[0].parts)
            )


if __name__ == "__main__":
    unittest.main()
