import http.server
import socketserver
import threading
import subprocess
import os
import time
import socket
from typing import List

class DeckTapeExporter:
    def __init__(self, output_dir: str):
        self.output_dir = os.path.abspath(output_dir)

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def export_slides(self, rel_urls: List[str]):
        if not rel_urls:
            return

        port = self._get_free_port()
        
        # Start temporary server
        handler = http.server.SimpleHTTPRequestHandler
        
        # Helper to avoid log spam
        class QuietHandler(handler):
            def log_message(self, format, *args):
                pass

        class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True

        # Need to serve from output_dir
        original_cwd = os.getcwd()
        os.chdir(self.output_dir)
        
        # One-time install of decktape if not already present
        # This drastically reduces overhead for multiple slides
        decktape_bin = os.path.join(original_cwd, "node_modules", ".bin", "decktape")
        if not os.path.exists(decktape_bin):
            print("Installing decktape locally for faster exports (one-time task)...")
            try:
                subprocess.run(
                    ["npm", "install", "--no-save", "decktape@3.12.0"],
                    cwd=original_cwd,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Warning: Local decktape install failed: {e.stderr}. Falling back to npx.")
                decktape_bin = None

        server = ThreadedHTTPServer(("", port), QuietHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print(f"Temporary server started at http://localhost:{port} for parallel decktape export.")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def process_url(rel_url: str):
            clean_rel_url = rel_url.lstrip("/")
            url = f"http://localhost:{port}/{clean_rel_url}"
            
            html_path = os.path.join(self.output_dir, clean_rel_url)
            pdf_path = os.path.splitext(html_path)[0] + ".pdf"
            
            # Optimized decktape command
            # Using --wait-until load and --load-pause 1000 since assets are local
            common_args = [
                "reveal",
                url, pdf_path,
                "--size", "1280x720",
                "--wait-until", "load",
                "--load-pause", "1000",
                "--chrome-arg=--no-sandbox",
                "--chrome-arg=--disable-gpu",
                "--chrome-arg=--allow-file-access-from-files"
            ]
            
            if decktape_bin:
                cmd = [decktape_bin] + common_args
            else:
                # Fallback to npx but with speed flags
                cmd = ["npx", "-y", "decktape@3.12.0"] + common_args
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True, clean_rel_url, pdf_path
            except subprocess.CalledProcessError as e:
                return False, clean_rel_url, e.stderr

        try:
            total = len(rel_urls)
            max_workers = os.cpu_count() or 4
            print(f"Starting optimized parallel export of {total} slides with {max_workers} workers...")
            
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
