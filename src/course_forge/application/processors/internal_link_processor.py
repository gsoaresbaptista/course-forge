import os
import re
from urllib.parse import quote

from course_forge.domain.entities import ContentNode

from .base import Processor


class InternalLinkProcessor(Processor):
    """Convert internal markdown links to HTML links using correct slugs.

    Supports:
    - [text](page) -> [text](page.html)
    - [text](page.md) -> [text](page.html)
    - [text](../other/page.md) -> [text](../other/page.html)
    - [text](/course/module/page) -> [text](/course/module/page.html)

    Also URL-encodes spaces so Mistune can parse them correctly.
    """

    LINK_PATTERN = re.compile(
        r"\[([^\]]+)\]\(([^)]+)\)",
        re.MULTILINE,
    )

    def __init__(self) -> None:
        self.root: ContentNode | None = None

    def set_root(self, root: ContentNode) -> None:
        self.root = root

    def execute(self, node: ContentNode, content: str) -> str:
        def replace_link(match: re.Match) -> str:
            text = match.group(1)
            href = match.group(2)

            if self._is_external_link(href):
                return match.group(0)

            if href.startswith("#"):
                return match.group(0)

            # Try to resolve node if we have the tree
            if self.root:
                resolved_href = self._resolve_link(node, href)
                if resolved_href:
                    return f"[{text}]({resolved_href})"

            # Fallback to simple replacement
            if href.endswith(".md"):
                href = href[:-3] + ".html"
            elif not self._has_extension(href) and not href.endswith("/"):
                href = href + ".html"

            href = self._encode_path(href)

            return f"[{text}]({href})"

        return self.LINK_PATTERN.sub(replace_link, content)

    def _resolve_link(self, current_node: ContentNode, href: str) -> str | None:
        """Resolve a relative or absolute path to a ContentNode and return its slug path."""
        # Clean up href
        path_part = href.split("#")[0]
        anchor = href.split("#")[1] if "#" in href else ""

        if path_part.startswith("/"):
            # Absolute path from root
            target_node = self._find_node_by_path(self.root, path_part)
        else:
            # Relative path
            target_node = self._resolve_relative_path(current_node, path_part)

        if target_node:
            slugs = target_node.slugs_path + [target_node.slug]

            # Construct relative path from current_node to target_node
            current_slugs = current_node.slugs_path + [current_node.slug]

            if current_node.is_file:
                current_dir_slugs = current_slugs[:-1]
            else:
                current_dir_slugs = current_slugs

            rel_path = self._compute_relative_slug_path(current_dir_slugs, slugs)

            # Append .html extension if it's a file
            if target_node.is_file:
                rel_path += ".html"

            if anchor:
                rel_path += f"#{anchor}"

            return rel_path

        return None

    def _find_node_by_path(self, root: ContentNode, path: str) -> ContentNode | None:
        # Implementation relying on relative resolution for now
        return None  # To be implemented if we need absolute path support

    def _resolve_relative_path(
        self, current_node: ContentNode, href: str
    ) -> ContentNode | None:
        if current_node.is_file:
            current_dir = current_node.parent
        else:
            current_dir = current_node

        if not current_dir:
            return None

        parts = href.split("/")

        node = current_dir
        for part in parts:
            if part == "." or part == "":
                continue
            elif part == "..":
                if node.parent:
                    node = node.parent
            else:
                found = None
                for child in node.children:
                    # Check against original filename/path basename
                    if os.path.basename(child.src_path) == part:
                        found = child
                        break
                    # Fallback to name check
                    if child.name == part:
                        found = child
                        break

                if found:
                    node = found
                else:
                    return None

        return node

    def _compute_relative_slug_path(
        self, start_slugs: list[str], target_slugs: list[str]
    ) -> str:
        # Find common prefix
        i = 0
        while (
            i < len(start_slugs)
            and i < len(target_slugs)
            and start_slugs[i] == target_slugs[i]
        ):
            i += 1

        # Steps up
        up_steps = len(start_slugs) - i

        # Steps down
        down_steps = target_slugs[i:]

        path_parts = [".."] * up_steps + down_steps
        if not path_parts:
            return "."  # Same directory?

        return "/".join(path_parts)

    def _is_external_link(self, href: str) -> bool:
        return href.startswith(("http://", "https://", "mailto:", "tel:"))

    def _has_extension(self, href: str) -> bool:
        path = href.split("#")[0].split("?")[0]
        last_part = path.split("/")[-1]
        return "." in last_part

    def _encode_path(self, href: str) -> str:
        """URL-encode spaces and special chars in path, preserving structure."""
        parts = href.split("/")
        encoded_parts = [quote(part, safe="") for part in parts]
        return "/".join(encoded_parts)
