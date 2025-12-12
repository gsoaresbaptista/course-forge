import argparse
import os
from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).parent.parent.parent

    template_dir = os.getenv("COURSE_FORGE_TEMPLATE_DIR")

    debug = os.getenv("COURSE_FORGE_DEBUG", "false").lower() == "true"
    watch_port = int(os.getenv("COURSE_FORGE_WATCH_PORT", "8001"))

    @classmethod
    def update_from_args(cls, args: argparse.Namespace):
        if hasattr(args, "template_dir") and args.template_dir:
            cls.template_dir = args.template_dir
        if hasattr(args, "content") and args.content:
            cls.content_path = args.content
        if hasattr(args, "output") and args.output:
            cls.output_path = args.output
        if hasattr(args, "debug") and args.debug is not None:
            cls.debug = args.debug
        if hasattr(args, "port") and args.port:
            cls.watch_port = args.port
