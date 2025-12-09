import os

from livereload import Server  # type: ignore

from .build import build


def watch(content_path: str, output_path: str):
    def rebuild():
        print("Rebuilding...")
        build(content_path, output_path)
        print("Rebuild done!")

    rebuild()

    server = Server()

    for root, _, files in os.walk(content_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                server.watch(full_path, rebuild)  # type: ignore

    server.serve(  # type: ignore
        root=output_path, port=8000, host="localhost", open_url_delay=0
    )
