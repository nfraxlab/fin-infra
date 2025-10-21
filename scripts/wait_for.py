#!/usr/bin/env python3
from __future__ import annotations

import socket
import sys
import time


def wait_for(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5.0):
                print(f"[wait-for] {host}:{port} is up")
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.5)
    raise SystemExit(f"[wait-for] Timeout waiting for {host}:{port} ({last_err})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: wait_for.py <host> <port> [timeout_seconds]", file=sys.stderr)
        raise SystemExit(2)
    host = sys.argv[1]
    port = int(sys.argv[2])
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
    wait_for(host, port, timeout)
