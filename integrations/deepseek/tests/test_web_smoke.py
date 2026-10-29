"""Test only local guard/cleanup helpers; never start dsh or a namespace."""

import importlib.util
import io
import http.cookiejar
import signal
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.response import addinfourl


SCRIPT = Path(__file__).parents[1] / "web_smoke.py"
spec = importlib.util.spec_from_file_location("web_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeGuardTests(unittest.TestCase):
    def test_explicit_approval_flag_required_before_any_runtime_access(self):
        result = subprocess.run([
            sys.executable, "-I", str(SCRIPT), "--node", "/nonexistent-node",
            "--cli-root", "/nonexistent-cli", "--state-root", "/nonexistent-state",
            "--existing-home", "/nonexistent-home",
        ], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no startup without --execute-approved", result.stderr)

    def test_completed_child_is_not_signalled(self):
        process = Mock()
        process.poll.return_value = 0
        with patch.object(smoke.os, "killpg") as kill:
            smoke.stop_owned_process(process)
            kill.assert_not_called()

    def test_only_owned_process_group_is_signalled(self):
        process = Mock(pid=12345)
        process.poll.return_value = None
        with patch.object(smoke.os, "killpg") as kill:
            smoke.stop_owned_process(process)
            kill.assert_called_once_with(12345, signal.SIGTERM)
            process.wait.assert_called_once_with(timeout=10)

    def test_unresponsive_owned_child_gets_bounded_kill(self):
        process = Mock(pid=12345)
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("owned-test", 10), 0]
        with patch.object(smoke.os, "killpg") as kill:
            smoke.stop_owned_process(process)
            self.assertEqual(kill.call_args_list[1].args, (12345, signal.SIGKILL))


class MemoryHTTP(urllib.request.HTTPHandler):
    """Pure in-memory transport: exercises urllib handlers without sockets."""

    def __init__(self, responses):
        super().__init__()
        self.responses = iter(responses)
        self.requests = []

    def http_open(self, req):
        self.requests.append(req)
        code, pairs, body = next(self.responses)
        headers = Message()
        for key, value in pairs:
            headers[key] = value
        response = addinfourl(io.BytesIO(body), headers, req.full_url, code)
        response.msg = "synthetic"
        return response


class WebAuthenticationTests(unittest.TestCase):
    def test_exact_launch_announcement(self):
        self.assertIsNone(smoke.launch_url_from_announcement("loading\n"))
        url = smoke.WEB_ROOT + "?token=synthetic-secret"
        self.assertEqual(smoke.launch_url_from_announcement("dsh web: " + url + "\n"), url)

    def test_malformed_and_foreign_launch_urls_are_rejected_without_leaking(self):
        secret = "synthetic-secret"
        values = ["http://example.invalid/?token=" + secret,
                  "http://127.0.0.1:13081/?token=" + secret,
                  "http://user@127.0.0.1:13080/?token=" + secret,
                  smoke.WEB_ROOT + "?token=", smoke.WEB_ROOT + "?token=" + secret + "&token=x",
                  smoke.WEB_ROOT + "?token=" + secret + "&extra=x",
                  smoke.WEB_ROOT + "?token=" + secret + "#fragment",
                  smoke.WEB_ROOT + "?token=" + secret + " (LAN: http://elsewhere)",
                  smoke.WEB_ROOT + "?token=" + secret + "\ndsh web: " + smoke.WEB_ROOT]
        for value in values:
            with self.subTest(value=value), self.assertRaises(smoke.SmokeFailure) as error:
                smoke.launch_url_from_announcement("dsh web: " + value)
            self.assertNotIn(secret, str(error.exception))

    def opener(self, responses):
        transport = MemoryHTTP(responses)
        opener = urllib.request.build_opener(transport, urllib.request.ProxyHandler({}),
                  urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), smoke.NoRedirect())
        return opener, transport

    def test_no_redirect_is_followed_and_cookie_is_retained(self):
        opener, transport = self.opener([(303, [("Location", "./"),
                       ("Set-Cookie", "fixture=session-value; Path=/; HttpOnly")], b"")])
        with smoke.http_response(opener, smoke.WEB_ROOT + "?token=secret", "exchange") as response:
            self.assertEqual(response.code, 303)
        self.assertEqual(len(transport.requests), 1)

    def test_complete_cookie_exchange_uses_only_expected_requests(self):
        opener, transport = self.opener([
            (401, [], b"unauthorized"),
            (303, [("Location", "./"), ("Set-Cookie", "fixture=session-value; Path=/; HttpOnly")], b""),
            (200, [], b'<title>DeepSeek Harness</title><script src="./assets/index-fixture.js"></script>'),
            (200, [], b"react/jsx-runtime"),
        ])
        evidence = {}
        # Use the fixture opener's actual cookie jar while retaining production construction.
        handler = next(h for h in opener.handlers if isinstance(h, urllib.request.HTTPCookieProcessor))
        with patch.object(smoke.http.cookiejar, "CookieJar", return_value=handler.cookiejar), \
             patch.object(smoke.urllib.request, "build_opener", return_value=opener):
            result = smoke.qualify_web(smoke.WEB_ROOT + "?token=secret", evidence)
        self.assertEqual(result, {"unauthenticated_root_http": 401, "launch_exchange_http": 303,
                                 "launch_cookie_in_memory": True, "web_entry_http": 200,
                                 "shell_asset_http": 200})
        self.assertEqual(len(transport.requests), 4)
        self.assertIsNone(transport.requests[0].get_header("Cookie"))
        self.assertEqual(transport.requests[2].get_header("Cookie"), "fixture=session-value")
        self.assertNotIn("secret", repr(result))
        self.assertEqual(transport.requests[2].full_url, smoke.WEB_ROOT)

    def test_unexpected_http_status_fails_once_and_keeps_safe_evidence(self):
        opener, transport = self.opener([(403, [], b"secret body")])
        evidence = {}
        with patch.object(smoke.urllib.request, "build_opener", return_value=opener), \
             self.assertRaises(smoke.SmokeFailure) as error:
            smoke.qualify_web(smoke.WEB_ROOT + "?token=secret", evidence)
        self.assertEqual(evidence, {"unauthenticated_root_http": 403})
        self.assertEqual(error.exception.status, 403)
        self.assertNotIn("secret", str(error.exception))
        self.assertEqual(len(transport.requests), 1)

    def test_transport_error_redacts_vendor_exception_and_url(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError("secret URL or credential")
        with self.assertRaises(smoke.SmokeFailure) as error:
            smoke.http_response(opener, smoke.WEB_ROOT + "?token=secret", "web_entry_http")
        self.assertNotIn("secret", str(error.exception))
        self.assertIsNone(error.exception.status)

    def test_bad_redirect_or_missing_cookie_fails_before_clean_page_request(self):
        for headers in [[("Location", "http://foreign.invalid/")], [("Location", "./")]]:
            opener, transport = self.opener([(401, [], b""), (303, headers, b"")])
            with patch.object(smoke.urllib.request, "build_opener", return_value=opener), \
                 self.assertRaises(smoke.SmokeFailure) as error:
                smoke.qualify_web(smoke.WEB_ROOT + "?token=secret", {})
            self.assertEqual(error.exception.stage, "launch_exchange_cookie")
            self.assertEqual(len(transport.requests), 2)


if __name__ == "__main__":
    unittest.main()
