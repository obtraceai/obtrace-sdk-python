import unittest
from unittest.mock import patch, MagicMock

from obtrace_sdk.client import ObtraceClient
from obtrace_sdk.types import ObtraceConfig


class ClientTests(unittest.TestCase):
    def test_enqueue_and_flush(self):
        c = ObtraceClient(
            ObtraceConfig(
                api_key="devkey",
                ingest_base_url="https://injet.obtrace.ai",
                service_name="py-test",
            )
        )
        c.log("info", "hello")
        c.metric("m", 1)
        c.span("s")

        with patch("urllib.request.urlopen") as urlopen:
            cm = MagicMock()
            cm.__enter__.return_value.status = 202
            cm.__exit__.return_value = False
            urlopen.return_value = cm
            c.flush()

        self.assertEqual(urlopen.call_count, 3)


if __name__ == "__main__":
    unittest.main()
