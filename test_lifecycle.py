import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import companion
import stop_lilbot


class LifecycleTests(unittest.TestCase):
    def test_stop_process_matching_is_limited_to_this_installation(self):
        process = Mock()
        process.cwd.return_value = str(stop_lilbot.ROOT)
        process.cmdline.return_value = ["python", "companion.py"]
        self.assertTrue(stop_lilbot.belongs_to_installation(process))
        process.cmdline.return_value = ["python", str(stop_lilbot.ROOT / "background_lilbot.pyw")]
        self.assertTrue(stop_lilbot.belongs_to_installation(process))
        process.cwd.return_value = str(stop_lilbot.ROOT.parent)
        process.cmdline.return_value = ["python", "companion.py"]
        self.assertFalse(stop_lilbot.belongs_to_installation(process))
        process.cwd.return_value = str(stop_lilbot.ROOT)
        process.cmdline.return_value = ["python", "other.py"]
        self.assertFalse(stop_lilbot.belongs_to_installation(process))

    def test_local_quit_requires_control_header_and_stops_server(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), companion.Handler) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            url = f"http://127.0.0.1:{server.server_port}/api/shutdown"
            try:
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url, data=b""), timeout=2)
                self.assertEqual(error.exception.code, 403)
                request = Request(url, data=b"", headers={"X-LilBot-Control": "1"})
                with urlopen(request, timeout=2) as response:
                    self.assertTrue(json.load(response)["ok"])
                worker.join(timeout=3)
                self.assertFalse(worker.is_alive())
            finally:
                server.shutdown()
                worker.join()
