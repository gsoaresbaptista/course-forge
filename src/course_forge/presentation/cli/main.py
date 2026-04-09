import argparse
import os

from course_forge.config import Config

from .commands import build, watch


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Course Forge CLI - Gerador de sites estáticos para materiais de curso.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", choices=["build", "watch"], help="Command to run: 'build' to generate the site, 'watch' to develop locally.")
    parser.add_argument(
        "-c", "-s", "--content", required=True, help="Path to input content directory"
    )
    parser.add_argument("-o", "--output", required=True, help="Path to output site directory")
    parser.add_argument("--template-dir", help="Path to custom template directory")
    parser.add_argument(
        "--base-url", 
        help="Base URL for static deployment. Utilizado para exportar o site para hospedagem estática (e.g., '/aulas-faesa')"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for verbose logging")
    parser.add_argument(
        "--exam", 
        action="store_true", 
        help="Gerar assignments (listas de exercícios) e provas baseadas no conteúdo do curso"
    )
    parser.add_argument(
        "--slide-export", 
        action="store_true", 
        help="Exportar todos os slides da apresentação para PDF (requer decktape iterativo)"
    )
    parser.add_argument(
        "--course",
        help="Filtrar por uma disciplina específica (e.g., 'compiladores')"
    )
    parser.add_argument("--port", type=int, help="Port for watch server (default: 8000)")
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
