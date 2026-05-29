from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def run_server(port: int = 8000):
    server = ThreadingHTTPServer(("0.0.0.0", port), NoCacheHandler)
    print(f"Serving showtimes dashboard at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
