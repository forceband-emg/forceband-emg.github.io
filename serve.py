#!/usr/bin/env python3
"""Local preview server with HTTP Range support.

Python's `http.server` ignores Range requests, which breaks video seeking
(dragging the progress bar) and start-offset playback. Production hosts
(GitHub Pages etc.) support ranges natively; use this only for local preview.

Usage:  python3 serve.py [port]      (default port 8000)
"""
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        range_header = self.headers.get("Range")
        if os.path.isdir(path) or not range_header:
            return super().send_head()

        m = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
        if not m or (not m.group(1) and not m.group(2)):
            return super().send_head()

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        size = os.fstat(f.fileno()).st_size
        if m.group(1):
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else size - 1
        else:  # suffix range: bytes=-N
            start = max(0, size - int(m.group(2)))
            end = size - 1
        end = min(end, size - 1)

        if start >= size or start > end:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        f.seek(start)
        self._range_remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        self._range_remaining = None
        while remaining > 0:
            chunk = source.read(min(65536, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    server = ThreadingHTTPServer(("0.0.0.0", port), RangeHandler)
    print(f"Serving with Range support on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
