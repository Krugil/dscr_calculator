"""Local no-cache dev/test server for the DSCR Calculator.

Real, hard-won lesson from the DSCR calculator build: a plain
`python -m http.server` (and a raw file:// URL even more so) repeatedly gave
false test readings -- a fixed stylesheet appeared broken because the browser
served a cached copy, and a genuinely broken change appeared fine for the same
reason. Every response here is explicitly marked non-cacheable so a test run
against this server always reflects the real, current files on disk.

Usage:
    python serve.py [port]      (default 8140)
Then open http://localhost:8140/
"""
import http.server
import socketserver
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8140


TEXT_EXTENSIONS = (".html", ".css", ".js", ".txt", ".json")


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_ROOT, **kwargs)

    def guess_type(self, path):
        # Real bug, found live: SimpleHTTPRequestHandler's default guess_type()
        # returns e.g. "text/javascript" with NO charset. Without an explicit
        # charset, the browser falls back to a non-UTF-8 interpretation for
        # that resource -- confirmed directly: script.js's em-dash character
        # (correct 3-byte UTF-8 on disk, \xe2\x80\x94) rendered as a mangled
        # replacement character in the page, breaking the Reset button's
        # placeholder text. Every text-based response needs charset=utf-8
        # declared explicitly, not left to the browser's own guess.
        mimetype = super().guess_type(path)
        base = mimetype.split(";")[0] if isinstance(mimetype, str) else mimetype
        if str(path).lower().endswith(TEXT_EXTENSIONS):
            return f"{base}; charset=utf-8"
        return mimetype

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[serve] {self.address_string()} - {fmt % args}\n")


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    # Threading, not plain TCPServer: a real Playwright browser opens several
    # concurrent connections (HTML + CSS + JS, sometimes kept alive) -- a
    # single-threaded server can end up blocking one request behind another,
    # confirmed live as repeated connection timeouts under real test load.
    with ThreadingHTTPServer(("", port), NoCacheHandler) as httpd:
        print(f"DSCR Calculator: http://localhost:{port}/")
        print(f"Serving {PROJECT_ROOT} (all responses marked no-cache). Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.shutdown()


if __name__ == "__main__":
    main()
