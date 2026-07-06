"""Trivial echo language pack for the Flash Capsule walking skeleton.

Speaks the supervisor<->pack IPC contract: newline-delimited JSON over a
Unix domain socket. Proves the seam; contains no real execution logic.
"""

import argparse
import json
import socket


def handle_line(line: str) -> str:
    """Turn one request line into one reply line (pure; socket-free)."""
    try:
        req = json.loads(line)
    except json.JSONDecodeError as exc:
        return json.dumps({"id": None, "error": {"type": "bad_request", "message": str(exc)}})

    req_id = req.get("id")
    if req.get("method") != "invoke":
        return json.dumps(
            {"id": req_id, "error": {"type": "unknown_method", "message": req.get("method")}}
        )
    return json.dumps({"id": req_id, "result": req.get("input")})


def _serve(socket_path: str) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(socket_path)
        with sock.makefile("rw") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                stream.write(handle_line(line) + "\n")
                stream.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    args = parser.parse_args()
    _serve(args.socket)


if __name__ == "__main__":
    main()
