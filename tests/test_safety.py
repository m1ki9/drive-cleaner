from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
