import argparse
import os

from course_forge.config import Config

from .commands import build, watch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "watch"])
    parser.add_argument(
        "-c", "-s", "--content", required=True, help="Path to input content"
    )
    parser.add_argument("-o", "--output", required=True, help="Path to output site")
    parser.add_argument("--template-dir", help="Path to template directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--port", type=int, help="Port for watch server")
    args = parser.parse_args()

    args.content = os.path.expanduser(args.content)
    args.output = os.path.expanduser(args.output)
    if args.template_dir:
        args.template_dir = os.path.expanduser(args.template_dir)

    Config.update_from_args(args)

    match args.command:
        case "build":
            build(
                content_path=args.content,
                output_path=args.output,
                template_dir=args.template_dir,
            )
        case "watch":
            watch(
                content_path=args.content,
                output_path=args.output,
                template_dir=args.template_dir,
            )
        case _:
            print(f"Error: invalid command ({args.command})!")
