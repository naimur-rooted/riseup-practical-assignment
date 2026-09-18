"""Local mock of the Airtable API (why: demo the retry queue without real creds).

Run:       python mock_airtable.py 8018
Then .env: AIRTABLE_API_URL=http://127.0.0.1:8018
           AIRTABLE_TOKEN=mock-token
           AIRTABLE_BASE_ID=mock-base
           AIRTABLE_TABLE_NAME=Items
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockAirtableHandler(BaseHTTPRequestHandler):
    """Accept every record (why: the mock only needs the success path)."""

    def do_POST(self) -> None:
        """Reply 200 with a fake record id (why: mirrors only check status)."""
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        payload: dict[str, object] = {"id": "recMOCK0001"}
        if body:
            payload["received"] = json.loads(body)
        self._respond(200, payload)

    def _respond(self, code: int, payload: dict[str, object]) -> None:
        """Write one JSON response (why: tiny helper keeps do_POST under 8 lines)."""
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        """Print every hit (why: the demo log must show the retry arriving)."""
        sys.stderr.write("MOCK-AIRTABLE " + (fmt % args) + "\n")


def main() -> None:
    """Start the mock on the given port (default 8018)."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8018
    server = HTTPServer(("127.0.0.1", port), MockAirtableHandler)
    print(f"mock airtable listening on http://127.0.0.1:{port} (Ctrl+C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    main()
