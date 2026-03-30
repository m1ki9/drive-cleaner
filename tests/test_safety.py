from pathlib import Path
from datetime import datetime
import unittest

from cleaner.cleanup.safety import SafetyPolicy


class SafetyPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SafetyPolicy()

    def test_blocks_windows_root(self) -> None:
        blocked, reason = self.policy.is_protected(Path("C:/Windows/System32/kernel32.dll"))
        self.assertTrue(blocked)
        self.assertIn("Protected", reason)

    def test_allows_regular_user_file(self) -> None:
        blocked, _ = self.policy.is_protected(Path("C:/Users/Public/Documents/readme.txt"))
        self.assertFalse(blocked)

    def test_blocks_protected_keyword_path(self) -> None:
        blocked, reason = self.policy.is_protected(Path("C:/Users/Public/system32/notepad.txt"))
        self.assertTrue(blocked)
        self.assertIn("keyword", reason.lower())

    def test_blocks_recent_file_deletion(self) -> None:
        recent = datetime.now().timestamp()
        blocked, reason = self.policy.validate_deletion(Path("C:/Users/Public/Documents/note.txt"), mtime=recent)
        self.assertTrue(blocked)
        self.assertIn("recent", reason.lower())

    def test_allows_old_file_deletion(self) -> None:
        old = datetime.now().timestamp() - (60 * 60 * 24 * 30)
        blocked, _ = self.policy.validate_deletion(Path("C:/Users/Public/Documents/archive.txt"), mtime=old)
        self.assertFalse(blocked)


if __name__ == "__main__":
    unittest.main()
