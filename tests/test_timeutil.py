import unittest

import _bootstrap  # noqa: F401
from core.timeutil import EPOCH_OFFSET, format_local, local_parts


class TimeUtilTests(unittest.TestCase):
    def test_unix_epoch_on_cpython(self):
        self.assertEqual(EPOCH_OFFSET, 0)
        self.assertEqual(local_parts(0, 0)[0], 1970)

    def test_format_local(self):
        self.assertEqual(format_local(0, 0), "1970-01-01T00:00:00+00:00")
        self.assertEqual(format_local(0, 8 * 3600), "1970-01-01T08:00:00+08:00")


if __name__ == "__main__":
    unittest.main()
