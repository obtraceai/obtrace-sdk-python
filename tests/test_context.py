import unittest

from obtrace_sdk.context import create_traceparent, ensure_propagation_headers


class ContextTests(unittest.TestCase):
    def test_create_traceparent(self):
        tp = create_traceparent()
        self.assertTrue(tp.startswith("00-"))
        parts = tp.split("-")
        self.assertEqual(len(parts[1]), 32)
        self.assertEqual(len(parts[2]), 16)

    def test_ensure_propagation_headers(self):
        out = ensure_propagation_headers({}, session_id="s1")
        self.assertIn("traceparent", {k.lower(): v for k, v in out.items()})
        self.assertIn("x-obtrace-session-id", {k.lower(): v for k, v in out.items()})


if __name__ == "__main__":
    unittest.main()
