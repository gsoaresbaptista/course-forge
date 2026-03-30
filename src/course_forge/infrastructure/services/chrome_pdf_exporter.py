import http.server
import socketserver
import threading
import subprocess
import os
import socket
import shutil
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

class ChromePdfExporter:
    def __init__(self, output_dir: str):
        self.output_dir = os.path.abspath(output_dir)
        self.chrome_path = self._find_chrome()

    def _find_chrome(self) -> str | None:
        """Find google-chrome or chromium binary."""
        paths = [
            "/opt/google/chrome/google-chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "google-chrome",
            "chromium",
        ]
        for path in paths:
            if shutil.which(path):
                return path
        return None

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def export_slides(self, rel_urls: List[str]):
        if not rel_urls or not self.chrome_path:
            return

        port = self._get_free_port()
        
        # Start temporary server
        handler = http.server.SimpleHTTPRequestHandler
        
        class QuietHandler(handler):
            def log_message(self, format, *args):
                pass

        class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True

        # Need to serve from output_dir
        original_cwd = os.getcwd()
        os.chdir(self.output_dir)
        
        server = ThreadedHTTPServer(("", port), QuietHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print(f"Temporary server started at http://localhost:{port} for parallel Chrome PDF export.")

        def process_url(rel_url: str):
            clean_rel_url = rel_url.lstrip("/")
            # Use ?print-pdf for Reveal.js
            url = f"http://localhost:{port}/{clean_rel_url}?print-pdf"
            
            html_path = os.path.join(self.output_dir, clean_rel_url)
            pdf_path = os.path.splitext(html_path)[0] + ".pdf"
            
            # Chrome headless print-to-pdf command
            cmd = [
                self.chrome_path,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={pdf_path}",
                "--display-header-footer", # Optional, but helps some layouts
                "--print-to-pdf-no-header", # We don't want default headers
                url
            ]
            
            try:
                # We need to wait a bit for Reveal.js to render
                # Chrome --print-to-pdf doesn't have a direct "wait-for-load" flag like DeckTape
                # but it usually waits for the load event.
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True, clean_rel_url, pdf_path
            except subprocess.CalledProcessError as e:
                return False, clean_rel_url, e.stderr

        try:
            total = len(rel_urls)
            max_workers = os.cpu_count() or 4
            print(f"Starting optimized parallel export of {total} slides using Chrome...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_url, url): url for url in rel_urls}
                
                done_count = 0
                for future in as_completed(futures):
                    success, url, result = future.result()
                    done_count += 1
                    if success:
                        print(f"[{done_count}/{total}] Successfully exported: {url}")
                    else:
                        print(f"[{done_count}/{total}] Error exporting {url}: {result}")

        finally:
            print("Stopping temporary server...")
            server.shutdown()
            server.server_close()
            os.chdir(original_cwd)
