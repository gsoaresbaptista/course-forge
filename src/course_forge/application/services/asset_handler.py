import os
import xml.etree.ElementTree as ET
from typing import Any


class AssetHandler:
    @staticmethod
    def resize_svg_data(
        svg_bytes: bytes, new_width: int | None = None, new_height: int | None = None
    ) -> bytes:
        root = ET.fromstring(svg_bytes)
        root.set("class", "svg-graph")

        if new_width is not None:
            root.set("width", str(new_width))
        elif "width" in root.attrib:
            del root.attrib["width"]

        if new_height is not None:
            root.set("height", str(new_height))
        elif "height" in root.attrib:
            del root.attrib["height"]

        return ET.tostring(root, encoding="utf-8")

    @staticmethod
    def process_asset(
        asset: dict[str, Any], node_slug: str, asset_index: int, out_dir: str
    ) -> tuple[str, str]:
        token = f"{{{{asset:{asset['type']}:{asset_index}}}}}"

        if asset["extension"] == "svg":
            svg = AssetHandler.resize_svg_data(
                asset["data"], asset.get("width"), asset.get("height")
            ).decode("utf-8")
            return token, f'<figure class="asset-svg">{svg}</figure>'

        static_dir = os.path.join(out_dir, "static")
        os.makedirs(static_dir, exist_ok=True)

        filename = f"{node_slug}_{asset_index}.{asset['extension']}"
        file_path = os.path.join(static_dir, filename)

        with open(file_path, "wb") as f:
            f.write(asset["data"])

        public_path = f"static/{filename}"
        return token, f'<figure class="asset-img"><img src="{public_path}" /></figure>'
