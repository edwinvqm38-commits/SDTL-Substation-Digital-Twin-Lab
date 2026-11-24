"""Local-only CAD viewer. Render native DXF via ezdxf drawing frontend."""
import argparse
import io
import json
import tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout, config
from backend.cad_reader import DXFReader

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 100 * 1024 * 1024

def render(path, hidden=()):
    doc = ezdxf.readfile(path)
    for name in hidden:
        if name in doc.layers:
            doc.layers.get(name).off()
    backend = svg.SVGBackend()
    settings = config.Configuration(background_policy=config.BackgroundPolicy.BLACK,
        lineweight_policy=config.LineweightPolicy.ABSOLUTE)
    Frontend(RenderContext(doc), backend, config=settings).draw_layout(doc.modelspace())
    return backend.get_string(layout.Page(0, 0), settings=layout.Settings(fit_page=True))

def inspect(path):
    result = DXFReader().read(path)
    return result.model_dump(mode="json", exclude={"metadata": {"source_path"}})

class Handler(BaseHTTPRequestHandler):
    def send_data(self, body, kind, status=200):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.send_data((ROOT / "frontend/cad_viewer/index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_data(b"Not found", "text/plain", 404)

    def do_POST(self):
        try:
            if self.path != "/api/render":
                raise ValueError("Unknown endpoint")
            if self.headers.get("Origin") not in (None, "http://" + self.headers.get("Host", "")):
                raise ValueError("Origin not allowed")
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= MAX_BYTES:
                raise ValueError("Invalid file size (max 100 MiB)")
            hidden = json.loads(self.headers.get("X-Hidden-Layers", "[]"))
            if not isinstance(hidden, list) or not all(isinstance(x, str) for x in hidden):
                raise ValueError("Invalid layers")
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "drawing.dxf"
                path.write_bytes(self.rfile.read(n))
                result = {"svg": render(path, hidden)}
                if self.headers.get("X-Render-Only") != "1":
                    result["document"] = inspect(path)
            self.send_data(json.dumps(result).encode(), "application/json")
        except Exception as exc:
            self.send_data(json.dumps({"error": str(exc)}).encode(), "application/json", 400)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"SDTL CAD: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()

if __name__ == "__main__":
    main()
