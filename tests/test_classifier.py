from pathlib import Path
import unittest

from cleaner import config
from cleaner.scanning.classifier import classify_path


class ClassifierTests(unittest.TestCase):
    def test_temp_classification(self) -> None:
        result = classify_path(Path("C:/Users/test/AppData/Local/Temp/x.tmp"))
        self.assertEqual(result, config.CATEGORY_TEMP)

    def test_cache_classification(self) -> None:
        result = classify_path(Path("C:/Users/test/AppData/Local/Microsoft/Windows/INetCache/a.dat"))
        self.assertEqual(result, config.CATEGORY_CACHE)

    def test_download_classification(self) -> None:
        result = classify_path(Path("C:/Users/test/Downloads/archive.zip"))
        self.assertEqual(result, config.CATEGORY_DUPLICATE_DOWNLOAD)


if __name__ == "__main__":
    unittest.main()
