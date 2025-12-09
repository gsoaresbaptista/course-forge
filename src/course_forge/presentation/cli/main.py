import argparse

from .commands import build, watch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "watch"])
    parser.add_argument("--content", required=True, help="Path to input content")
    parser.add_argument("--output", required=True, help="Path to output site")
    args = parser.parse_args()

    match args.command:
        case "build":
            build(content_path=args.content, output_path=args.output)
        case "watch":
            watch(content_path=args.content, output_path=args.output)
        case _:
            print(f"Error: invalid command ({args.command})!")
