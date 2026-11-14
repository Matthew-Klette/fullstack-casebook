"""A small stand-in for the payroll service, used by `make dev` and by tests.

It records every request, and it de-duplicates by Idempotency-Key the way a well-behaved
payroll API would. `slow_first` processes the first request, then stalls before replying,
which is how a lost acknowledgement looks from the client side.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class PayrollStub:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 0, slow_first: float = 0.0, hang: bool = False
    ):
        self.slow_first = slow_first
        self.hang = hang
        self.requests = 0
        self.batches: dict[str, dict] = {}  # remote batch id -> payload
        self._by_key: dict[str, str] = {}
        self._lock = threading.Lock()
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                length = int(self.headers.get("content-length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                key = self.headers.get("Idempotency-Key")
                with stub._lock:
                    stub.requests += 1
                    first = stub.requests == 1
                    if key and key in stub._by_key:
                        batch_id = stub._by_key[key]
                    else:
                        batch_id = f"batch-{len(stub.batches) + 1}"
                        stub.batches[batch_id] = payload
                        if key:
                            stub._by_key[key] = batch_id
                if stub.hang:
                    time.sleep(30)
                if first and stub.slow_first:
                    time.sleep(stub.slow_first)
                body = json.dumps({"batch_id": batch_id}).encode()
                try:
                    self.send_response(200)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> PayrollStub:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args()
    stub = PayrollStub(port=args.port).start()
    print(f"payroll stub listening on {stub.url}", flush=True)
    threading.Event().wait()
