import unittest

import _bootstrap  # noqa: F401
from web.api import _split_path
from web.server import parse_request_line


class HttpParseTests(unittest.TestCase):
    def test_request_line(self):
        method, path, version = parse_request_line(b"GET /api/v1/state HTTP/1.1\r\n")
        self.assertEqual((method, path, version), ("GET", "/api/v1/state", "HTTP/1.1"))

    def test_bad_request_line(self):
        with self.assertRaises(ValueError):
            parse_request_line(b"GET /only-two-parts")

    def test_query_split(self):
        path, query = _split_path("/api/v1/history?range=24h")
        self.assertEqual(path, "/api/v1/history")
        self.assertEqual(query["range"], "24h")


if __name__ == "__main__":
    unittest.main()
