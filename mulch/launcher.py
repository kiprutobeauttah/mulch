import os
import socket
import sys
import threading
import webbrowser
import time

from mulch.app import serve


def _wait_for_server(host, port, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    port = int(os.environ.get("MULCH_PORT", "5005"))
    url = f"http://127.0.0.1:{port}"

    print("Mulch starting…", flush=True)
    print(f"Serving at {url}", flush=True)

    server_thread = threading.Thread(target=serve, kwargs={"port": port}, daemon=True)
    server_thread.start()

    if "--no-browser" not in sys.argv:
        if _wait_for_server("127.0.0.1", port):
            webbrowser.open(url)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nMulch stopped.", flush=True)


if __name__ == "__main__":
    main()