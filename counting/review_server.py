"""Loopback source-only manual review, with HTTP Range and local JSON export."""
import argparse
import hashlib
import json
import re
import threading
from collections import OrderedDict
from urllib.parse import urlsplit, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve(video, template, host="127.0.0.1", port=8780, playback=None):
    video, template = Path(video), Path(template)
    playback = Path(playback) if playback else video
    metadata = json.loads(template.read_text(encoding="utf-8-sig"))
    html = (Path(__file__).parent / "review.html").read_bytes()
    integrity = {"signature": None, "verified": False}
    lock = threading.Lock()
    frame_lock = threading.Lock()
    frame_cache = OrderedDict()
    capture = None
    next_frame = None
    def frame_jpeg(frame):
        nonlocal capture, next_frame
        import cv2
        with frame_lock:
            if frame in frame_cache:
                return frame_cache[frame]
            if capture is None:
                capture = cv2.VideoCapture(str(video))
            if next_frame != frame:
                if not capture.set(cv2.CAP_PROP_POS_FRAMES, frame):
                    raise ValueError("Source decoder cannot seek")
            ok, image = capture.read()
            if not ok:
                raise ValueError("Source frame cannot be decoded")
            next_frame = frame + 1
            ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not ok:
                raise ValueError("JPEG encoding failed")
            frame_cache[frame] = encoded.tobytes()
            while len(frame_cache) > 8:
                frame_cache.popitem(last=False)
            return frame_cache[frame]
    def ready():
        if not video.is_file():
            return False
        if not playback.is_file():
            return False
        stat = video.stat()
        expected_size = metadata.get("source_bytes")
        if expected_size and stat.st_size != expected_size:
            return False
        play_stat = playback.stat()
        signature = stat.st_size, stat.st_mtime_ns, play_stat.st_size, play_stat.st_mtime_ns
        with lock:
            if signature != integrity["signature"]:
                digest = hashlib.sha256()
                with video.open("rb") as file:
                    for block in iter(lambda: file.read(1024 * 1024), b""):
                        digest.update(block)
                verified = digest.hexdigest() == metadata["source_video_sha256"]
                if playback != video:
                    digest = hashlib.sha256()
                    with playback.open("rb") as file:
                        for block in iter(lambda: file.read(1024 * 1024), b""):
                            digest.update(block)
                    verified = verified and digest.hexdigest() == metadata.get("playback_sha256")
                integrity.update(signature=signature, verified=verified)
        return integrity["verified"]

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.respond(head=True)

        def do_GET(self):
            self.respond(head=False)

        def respond(self, head=False):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self.send_bytes((Path(__file__).parent / "review.html").read_bytes(), "text/html; charset=utf-8", head)
            if path == "/metadata.json":
                value = {**metadata, "source_integrity_verified": ready(),
                         "downloaded_bytes": video.stat().st_size if video.exists() else 0}
                return self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), "application/json", head)
            if path == "/frame.jpg":
                try:
                    frame = int(parse_qs(urlsplit(self.path).query)["frame0"][0])
                    interval = metadata["reviewed_interval"]
                    if not interval["start_frame0"] <= frame <= interval["end_frame0"] or not ready():
                        raise ValueError("Frame outside reviewed scope or unverified source")
                    return self.send_bytes(frame_jpeg(frame), "image/jpeg", head)
                except (ValueError, KeyError) as error:
                    self.send_error(400, str(error))
                    return
            if path != "/source.mp4":
                self.send_error(404)
                return
            if not ready():
                self.send_error(503, "Source transfer/integrity check not finished")
                return
            size = playback.stat().st_size
            start, end, status = 0, size - 1, 200
            header = self.headers.get("Range")
            if header:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
                if not match or not any(match.groups()):
                    self.send_error(416)
                    return
                a, b = match.groups()
                if a:
                    start, end = int(a), min(int(b), size - 1) if b else size - 1
                else:
                    start, end = max(0, size - int(b)), size - 1
                if start >= size or end < start:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206
            self.send_response(status)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if head:
                return
            try:
                with playback.open("rb") as file:
                    file.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        block = file.read(min(256 * 1024, remaining))
                        if not block:
                            break
                        self.wfile.write(block)
                        remaining -= len(block)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def send_bytes(self, data, kind, head):
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head:
                self.wfile.write(data)

        def log_message(self, *_):
            pass

    if host != "127.0.0.1":
        raise ValueError("Manual review server binds loopback only")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"SOURCE_ONLY_REVIEW http://{host}:{port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--playback", help="Optional verified browser-compatible remux; source hash remains original")
    args = parser.parse_args()
    serve(args.video, args.template, port=args.port, playback=args.playback)
