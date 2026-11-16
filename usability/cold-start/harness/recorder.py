"""
recorder.py: record what a cold-start agent sends to the record and what comes back.

The recorder sits on loopback between the agent's MCP client and the token proxy:

    agent's MCP client -> recorder (127.0.0.1:8798) -> token proxy (127.0.0.1:8799) -> record /mcp

It forwards each request unchanged and returns the upstream answer unchanged, so it does
not alter what the agent sees. For each exchange it appends one JSON line to its log: when
the request arrived and was answered, the HTTP method and path, the MCP headers, the request
body, the status, and the response body. JSON bodies are stored parsed, others as text.

It never handles a credential. The token proxy adds the bearer token downstream. An
Authorization header that arrives from the client is neither forwarded nor logged; the log
records only that one arrived. It uses the standard library only.

Usage:
    python recorder.py --listen 127.0.0.1:8798 --upstream http://127.0.0.1:8799/mcp --log wire.jsonl
"""

from __future__ import annotations

import argparse
import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

# Request headers passed upstream, and response headers passed back. Nothing else crosses.
_FORWARD = ("Content-Type", "Accept", "MCP-Protocol-Version", "Mcp-Session-Id", "Last-Event-ID")
_RETURN = ("Content-Type", "Mcp-Session-Id", "WWW-Authenticate")
_LOOPBACK = ("127.0.0.1", "localhost")


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: the recorder talks to one upstream only."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102 (urllib's signature)
        return None


def _now() -> str:
    """The current UTC time, to the millisecond."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _body(raw: bytes) -> Any:
    """A body as parsed JSON when it is JSON, as text otherwise, and None when empty."""
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text


def make_server(port: int, upstream: str, log_path: str) -> ThreadingHTTPServer:
    """Build, but do not start, a recorder on 127.0.0.1:`port` that forwards to `upstream`."""
    opener = urllib.request.build_opener(_NoRedirects)
    upstream_path = urlsplit(upstream).path
    lock = threading.Lock()
    sequence = [0]

    class Handler(BaseHTTPRequestHandler):
        """Relay one request, answer it with the upstream's answer, and log the exchange."""

        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            """Keep the default access log quiet; the JSON log is the record of the run."""

        def _relay(self) -> None:
            """Forward the request upstream unchanged, return the answer, then log both."""
            arrived = _now()
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            sent = {name: self.headers[name] for name in _FORWARD if self.headers.get(name) is not None}
            entry: dict[str, Any] = {
                "arrived_at": arrived, "method": self.command, "path": self.path, "request_headers": sent,
                "authorization_header_arrived": "Authorization" in self.headers, "request": _body(raw),
            }
            if urlsplit(self.path).path != upstream_path:
                status, headers, payload = 404, {"Content-Type": "application/json"}, b'{"error": "not found"}'
            else:
                request = urllib.request.Request(
                    upstream, data=raw if self.command == "POST" else None, method=self.command, headers=sent)
                try:
                    with opener.open(request, timeout=120) as response:
                        status, payload = response.status, response.read()
                        headers = {name: response.headers[name] for name in _RETURN if response.headers.get(name)}
                except urllib.error.HTTPError as error:
                    status, payload = error.code, error.read()
                    headers = {name: error.headers[name] for name in _RETURN if error.headers.get(name)}
                except Exception as error:  # the upstream did not answer at all
                    status, headers = 502, {"Content-Type": "application/json"}
                    payload = json.dumps({"error": "upstream unreachable", "detail": type(error).__name__}).encode()
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            entry.update({"status": status, "response_headers": headers, "response": _body(payload),
                          "answered_at": _now()})
            with lock:
                sequence[0] += 1
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(json.dumps({"seq": sequence[0], **entry}, ensure_ascii=False) + "\n")

        do_POST = do_GET = do_DELETE = _relay

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> None:
    """Parse the arguments, refuse anything but loopback, and serve until interrupted."""
    parser = argparse.ArgumentParser(description="Record a cold-start agent's exchanges with the record.")
    parser.add_argument("--listen", default="127.0.0.1:8798")
    parser.add_argument("--upstream", required=True, help="the loopback token proxy's /mcp URL")
    parser.add_argument("--log", required=True, help="the JSON-lines log to append to")
    args = parser.parse_args(argv)
    host, _, port = args.listen.rpartition(":")
    if host not in _LOOPBACK or not port.isdigit():
        parser.error("--listen must be a loopback host:port")
    if urlsplit(args.upstream).hostname not in _LOOPBACK:
        parser.error("--upstream must be the loopback token proxy, which adds the credentials")
    server = make_server(int(port), args.upstream, args.log)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
