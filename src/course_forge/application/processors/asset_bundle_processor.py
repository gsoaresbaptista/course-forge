import hashlib
import os
import re
import threading
from pathlib import Path

import csscompressor
import jsmin

from course_forge.config import Config
from course_forge.domain.entities import ContentNode

from .base import Processor


class AssetBundleProcessor(Processor):
    def __init__(self, template_dir: str, output_dir: str):
        self.template_dir = Path(os.path.abspath(template_dir))
        self.output_dir = Path(os.path.abspath(output_dir))
        self._lock = threading.Lock()
        self._written_bundles: set[str] = set()

    def _resolve_asset_path(self, asset_rel: str) -> Path | None:
        rel_path = asset_rel.lstrip("/")
        candidate = self.template_dir / rel_path
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def _minify_js(self, asset_path: Path) -> str:
        with open(asset_path, "r", encoding="utf-8") as file:
            content = file.read()

        content = re.sub(
            r"\/\/[#@]\s*sourceMappingURL=.*$", "", content, flags=re.MULTILINE
        )
        content = re.sub(
            r"\/\*#\s*sourceMappingURL=.*?\*\/", "", content, flags=re.MULTILINE
        )

        if asset_path.name.endswith(".min.js"):
            return content

        try:
            return jsmin.jsmin(content, quote_chars="'\"`")
        except Exception as exc:
            print(f"Warning: Failed to minify {asset_path.name}: {exc}")
            return content

    def _minify_css(self, asset_path: Path) -> str:
        with open(asset_path, "r", encoding="utf-8") as file:
            content = file.read()

        content = re.sub(
            r"\/\/[#@]\s*sourceMappingURL=.*$", "", content, flags=re.MULTILINE
        )
        content = re.sub(
            r"\/\*#\s*sourceMappingURL=.*?\*\/", "", content, flags=re.MULTILINE
        )

        if asset_path.name.endswith(".min.css"):
            return content

        try:
            return csscompressor.compress(content)
        except Exception as exc:
            print(f"Warning: Failed to compress {asset_path.name}: {exc}")
            return content

    def _build_bundle_rel(self, asset_type: str, asset_paths: list[str]) -> str:
        digest = hashlib.sha1("|".join(asset_paths).encode("utf-8")).hexdigest()[:12]
        labels = [Path(asset).stem.replace(".min", "") for asset in asset_paths[:3]]
        label = "-".join(labels) if labels else asset_type
        label = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-") or asset_type
        return f"{asset_type}/bundles/{label}-{digest}.bundle.min.{asset_type}"

    def _write_bundle(self, asset_type: str, asset_paths: list[str]) -> str | None:
        if not asset_paths:
            return None

        bundle_rel = self._build_bundle_rel(asset_type, asset_paths)
        if bundle_rel in self._written_bundles:
            return bundle_rel

        contents: list[str] = []
        for asset_rel in asset_paths:
            asset_path = self._resolve_asset_path(asset_rel)
            if not asset_path:
                print(f"Warning: Failed to resolve asset for bundling: {asset_rel}")
                continue

            header = f"\n/* --- BUNDLED: {asset_path.name} --- */\n"
            if asset_type == "js":
                contents.append(header + self._minify_js(asset_path) + "\n;\n")
            else:
                contents.append(header + self._minify_css(asset_path) + "\n")

        if not contents:
            return None

        dst_path = self.output_dir / bundle_rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dst_path, "w", encoding="utf-8") as file:
            file.write("".join(contents))

        self._written_bundles.add(bundle_rel)
        return bundle_rel

    def _extract_assets(self, content: str, asset_type: str) -> list[str]:
        base_url_pattern = re.escape(Config.base_url) if Config.base_url else ""
        if asset_type == "js":
            pattern = re.compile(
                rf'<script\s+(?!.*?data-no-bundle)[^>]*?src=["\'](?:{base_url_pattern})?(/js/[^":\' ]+)["\'][^>]*>\s*</script>',
                re.IGNORECASE,
            )
        else:
            pattern = re.compile(
                rf'<link\s+(?!.*?data-no-bundle)[^>]*?href=["\'](?:{base_url_pattern})?(/css/[^":\' ]+)["\'][^>]*>',
                re.IGNORECASE,
            )

        seen: set[str] = set()
        assets: list[str] = []
        for match in pattern.finditer(content):
            asset_rel = match.group(1)
            if asset_rel not in seen:
                seen.add(asset_rel)
                assets.append(asset_rel)
        return assets

    def _replace_with_bundle(
        self, content: str, asset_type: str, bundle_rel: str | None
    ) -> str:
        base_url_pattern = re.escape(Config.base_url) if Config.base_url else ""
        if asset_type == "js":
            pattern = re.compile(
                rf'<script\s+(?!.*?data-no-bundle)[^>]*?src=["\'](?:{base_url_pattern})?(/js/[^":\' ]+)["\'][^>]*>\s*</script>',
                re.IGNORECASE,
            )
        else:
            pattern = re.compile(
                rf'<link\s+(?!.*?data-no-bundle)[^>]*?href=["\'](?:{base_url_pattern})?(/css/[^":\' ]+)["\'][^>]*>',
                re.IGNORECASE,
            )

        if not bundle_rel:
            return content

        prefix = Config.base_url if Config.base_url else ""
        if asset_type == "js":
            replacement_tag = f'<script src="{prefix}/{bundle_rel}"></script>'
        else:
            replacement_tag = f'<link rel="stylesheet" href="{prefix}/{bundle_rel}">'

        replacement_made = False

        def replacer(match: re.Match[str]) -> str:
            nonlocal replacement_made
            if replacement_made:
                return ""
            replacement_made = True
            return replacement_tag

        return pattern.sub(replacer, content)

    def execute(self, node: ContentNode, content: str) -> str:
        js_assets = self._extract_assets(content, "js")
        css_assets = self._extract_assets(content, "css")

        with self._lock:
            js_bundle_rel = self._write_bundle("js", js_assets)
            css_bundle_rel = self._write_bundle("css", css_assets)

        new_content = self._replace_with_bundle(content, "js", js_bundle_rel)
        new_content = self._replace_with_bundle(new_content, "css", css_bundle_rel)
        return new_content
