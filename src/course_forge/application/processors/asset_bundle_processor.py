import os
import re
from pathlib import Path

import csscompressor
import jsmin

from course_forge.domain.entities import ContentNode

from .base import Processor


class AssetBundleProcessor(Processor):
    def __init__(self, template_dir: str, output_dir: str):
        # Resolve to absolute paths
        self.template_dir = Path(os.path.abspath(template_dir))
        self.output_dir = Path(os.path.abspath(output_dir))
        self.js_bundle_rel = "js/bundle.min.js"
        self.css_bundle_rel = "css/bundle.min.css"
        self._bundles_written = False
        self._js_content = ""
        self._css_content = ""

    def _prepare_bundles(self):
        """Bundle all local JS and CSS files found in the template directory."""
        js_priority = {
            "katex.min.js": 0,
            "auto-render.min.js": 1,
            "rough.min.js": 2,
            "apply_sketch.js": 3,
            "navigation.js": 4,
            "ui.js": 5,
        }

        def js_sort_key(f: Path):
            return js_priority.get(f.name, 100), f.name

        js_dir = self.template_dir / "js"
        if js_dir.exists():
            files = sorted(
                [f for f in js_dir.iterdir() if f.is_file() and f.suffix == ".js"],
                key=js_sort_key,
            )
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        self._js_content += (
                            f"\n/* --- BUNDLED: {f.name} --- */\n" + file.read() + "\n"
                        )
                except Exception as e:
                    print(f"Warning: Failed to read {f} for bundling: {e}")

        css_priority = {
            "katex.min.css": 0,
            "base.css": 1,
        }

        def css_sort_key(f: Path):
            return css_priority.get(f.name, 100), f.name

        css_dir = self.template_dir / "css"
        if css_dir.exists():
            files = sorted(
                [f for f in css_dir.iterdir() if f.is_file() and f.suffix == ".css"],
                key=css_sort_key,
            )
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        self._css_content += (
                            f"\n/* --- BUNDLED: {f.name} --- */\n" + file.read() + "\n"
                        )
                except Exception as e:
                    print(f"Warning: Failed to read {f} for bundling: {e}")

    def _write_bundles(self):
        """Minify and write the collected bundles to the output directory."""
        if self._js_content:
            try:
                minified = jsmin.jsmin(self._js_content, quote_chars="'\"`")
                dst_path = self.output_dir / self.js_bundle_rel
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(minified)
            except Exception as e:
                print(f"Warning: Failed to minify/write JS bundle: {e}")

        if self._css_content:
            try:
                minified = csscompressor.compress(self._css_content)
                dst_path = self.output_dir / self.css_bundle_rel
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(minified)
            except Exception as e:
                print(f"Warning: Failed to minify/write CSS bundle: {e}")

    def execute(self, node: ContentNode, content: str) -> str:
        """Replace local asset tags with a single bundle tag."""
        if not self._bundles_written:
            self._prepare_bundles()
            self._write_bundles()
            self._bundles_written = True

        # Improved regex: handle single/double quotes and optional attributes
        js_pattern = re.compile(
            r'<script\s+[^>]*?src=["\'](/js/[^":\' ]+)["\'][^>]*>\s*</script>',
            re.IGNORECASE,
        )
        css_pattern = re.compile(
            r'<link\s+[^>]*?href=["\'](/css/[^":\' ]+)["\'][^>]*>', re.IGNORECASE
        )

        new_content = content

        # Handle JS bundling replacement
        if js_pattern.search(new_content):
            replacement_made = False

            def custom_sub_js(m):
                nonlocal replacement_made
                if not replacement_made:
                    replacement_made = True
                    return f'<script src="/{self.js_bundle_rel}"></script>'
                return ""

            new_content = js_pattern.sub(custom_sub_js, new_content)

        # Handle CSS bundling replacement
        if css_pattern.search(new_content):
            replacement_made = False

            def custom_sub_css(m):
                nonlocal replacement_made
                if not replacement_made:
                    replacement_made = True
                    return f'<link rel="stylesheet" href="/{self.css_bundle_rel}">'
                return ""

            new_content = css_pattern.sub(custom_sub_css, new_content)

        return new_content
