import argparse

from .commands import build


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "watch"])
    parser.add_argument("--content", required=True, help="Path to input content")
    parser.add_argument("--output", required=True, help="Path to output site")
    args = parser.parse_args()

    if args.command == "build":
        build(content_path=args.content, output_path=args.output)
