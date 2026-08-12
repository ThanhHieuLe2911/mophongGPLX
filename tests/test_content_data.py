import json
import unittest
from importlib.resources import files

from gplx_sim.data_builder import validate_catalog


class ContentDataTests(unittest.TestCase):
    def test_catalog_has_expected_structure(self) -> None:
        catalog = json.loads(
            files("gplx_sim.data").joinpath("content_catalog.json").read_text(encoding="utf-8")
        )
        validate_catalog(catalog)

        self.assertEqual(len(catalog["situations"]), 120)
        self.assertEqual(
            sum(len(situation["parts"]) for situation in catalog["situations"]),
            480,
        )
        self.assertEqual(
            sum(
                len(part["answers"])
                for situation in catalog["situations"]
                for part in situation["parts"]
            ),
            1920,
        )


if __name__ == "__main__":
    unittest.main()
