import importlib.util
import json
from pathlib import Path
import struct
import time
import unittest
from unittest.mock import Mock, patch


SPEC = importlib.util.spec_from_file_location(
    "mcp_refresh", Path(__file__).resolve().parents[1] / "mcp_refresh.py")
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


class WebSocketControlTests(unittest.TestCase):
    def test_client_frames_are_masked_for_all_length_forms(self):
        for length in (0, 125, 126, 65535, 65536):
            with self.subTest(length=length):
                payload = b"p" * length
                encoded = refresh.masked_frame(payload)
                self.assertEqual(encoded[0], 0x81)
                self.assertTrue(encoded[1] & 0x80)
                offset = 2 if length < 126 else 4 if length < 65536 else 10
                mask = encoded[offset:offset + 4]
                decoded = bytes(v ^ mask[i % 4]
                                for i, v in enumerate(encoded[offset + 4:]))
                self.assertEqual(decoded, payload)

    def client_with_frames(self, frames):
        client = refresh.ControlClient.__new__(refresh.ControlClient)
        client.timeout = 1
        client.deadline = time.monotonic() + 1
        client.buffer = frames
        client.next_id = 0
        client.sock = Mock()
        client.sock.recv.return_value = b""
        return client

    def test_fragmented_json_and_interleaved_ping(self):
        client = self.client_with_frames(
            b'\x01\x06{"id":' + b'\x89\x01p' + b'\x80\x02' + b'1}')
        self.assertEqual(client.receive(), {"id": 1})
        pong = client.sock.sendall.call_args.args[0]
        self.assertEqual(pong[0], 0x8a)
        self.assertTrue(pong[1] & 0x80)

    def test_oversize_and_masked_server_frames_are_rejected(self):
        for frame in (b'\x81\x7f' + struct.pack("!Q", refresh.MAX_MESSAGE + 1),
                      b'\x81\x82'):
            with self.subTest(frame=frame):
                client = self.client_with_frames(frame)
                with self.assertRaises(refresh.ProtocolError):
                    client.receive()

    def test_midframe_eof_fails_instead_of_spinning(self):
        client = self.client_with_frames(b'\x81\x05x')
        with self.assertRaises(refresh.ProtocolError):
            client.receive()

    def test_reload_matches_installed_schema_and_never_starts_a_turn(self):
        client = self.client_with_frames(b'\x81\x14{"id":1,"result":{}}')
        sent = []
        with patch.object(client, "send", side_effect=sent.append):
            self.assertEqual(client.rpc("config/mcpServer/reload"), {})
            with self.assertRaises(ValueError):
                client.rpc("turn/start", {})
        self.assertEqual(sent, [{"id": 1, "method": "config/mcpServer/reload"}])

    def test_summary_drops_credentials_tools_sessions_and_errors(self):
        rows = refresh.summarize_status({"data": [{
            "name": "serena", "tools": {"x": {"description": "SECRET"}},
            "authStatus": "SECRET", "sessionId": "SECRET", "httpOrigin": "SECRET",
            "toolsError": "SECRET", "runtimeStatus": "failed",
        }]})
        self.assertNotIn("SECRET", json.dumps(rows))
        self.assertEqual(rows, [{"name": "serena", "tool_count": 1,
                                "runtime_status": "failed", "discovery_failed": True}])


if __name__ == "__main__":
    unittest.main()
