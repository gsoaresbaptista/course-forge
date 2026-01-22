import hashlib
import os
import re

from course_forge.application.loaders import MarkdownLoader
from course_forge.application.processors import Processor
from course_forge.application.renders import HTMLTemplateRenderer, MarkdownRenderer
from course_forge.application.writers import OutputWriter
from course_forge.domain.entities import ContentNode
from course_forge.domain.repositories import ContentTreeRepository
from course_forge.infrastructure.config.config_loader import ConfigLoader


class BuildSiteUseCase:
    def __init__(
        self,
        repository: ContentTreeRepository,
        loader: MarkdownLoader,
        markdown_renderer: MarkdownRenderer,
        html_renderer: HTMLTemplateRenderer,
        writer: OutputWriter,
    ) -> None:
        self.repository = repository
        self.loader = loader
        self.markdown_renderer = markdown_renderer
        self.html_renderer = html_renderer
        self.writer = writer

    def execute(
        self,
        root_path: str,
        pre_processors: list[Processor],
        post_processors: list[Processor],
        template_dir: str | None = None,
    ) -> None:
        config_path = os.path.join(root_path, "config.yaml")
        config = ConfigLoader().load(config_path)

        # Inject config into html_renderer if supported
        if hasattr(self.html_renderer, "config"):
            self.html_renderer.config = config

        tree = self.repository.load(root_path)

        self._detect_aliases(tree.root)

        # Inject root node into processors that need it
        for processor in pre_processors + post_processors:
            if hasattr(processor, "set_root"):
                processor.set_root(tree.root)

        existing_checksums = {}
        if hasattr(self.writer, "load_checksums"):
            existing_checksums = self.writer.load_checksums(root_path)

        new_checksums = {}

        self.writer.copy_assets(self.html_renderer.template_dir, skip_bundled=True)

        self._process_node(
            tree.root,
            pre_processors,
            post_processors,
            global_config=config,
            existing_checksums=existing_checksums,
            new_checksums=new_checksums,
        )

        if hasattr(self.writer, "save_checksums"):
            self.writer.save_checksums(root_path, new_checksums)

        courses = self._collect_top_level_courses(tree.root)

        if courses:
            index_html = self.html_renderer.render_index(courses)
            for processor in post_processors:
                index_html = processor.execute(tree.root, index_html)
            self.writer.write_index(index_html)

    def _collect_top_level_courses(self, node: ContentNode) -> list[dict]:
        courses = []
        # We only want direct children of root that are courses
        for child in node.children:
            course_name = self._clean_name(child.name)

            # Check for config.yaml to get custom name and visibility
            if not child.is_file and child.src_path:
                local_config_path = os.path.join(child.src_path, "config.yaml")
                if os.path.exists(local_config_path):
                    local_config = ConfigLoader().load(local_config_path)
                    if local_config.get("hidden"):
                        continue
                    if local_config.get("name"):
                        course_name = local_config.get("name")

            if not child.is_file:
                has_md = any(
                    c.is_file and c.file_extension == ".md" for c in child.children
                )

                if has_md:
                    courses.append(
                        {
                            "name": course_name,
                            "slug": child.slug,
                            "node": child,
                        }
                    )
                elif any(
                    not gc.is_file
                    and any(
                        ggc.is_file and ggc.file_extension == ".md"
                        for ggc in gc.children
                    )
                    for gc in child.children
                ):
                    courses.append(
                        {
                            "name": course_name,
                            "slug": child.name,
                            "node": child,
                        }
                    )
        return courses

    def _detect_aliases(self, root: ContentNode) -> None:
        """Traverse the tree and detect nodes that point to the same physical location.
        The canonical node is the one with the shallowest depth.
        """
        all_nodes: list[ContentNode] = []

        def collect(node: ContentNode):
            if not node.is_file and node.discovery_path:
                all_nodes.append(node)
            for child in node.children:
                collect(child)

        collect(root)

        # Group by discovery_path
        groups: dict[str, list[ContentNode]] = {}
        for node in all_nodes:
            path = node.discovery_path
            if path not in groups:
                groups[path] = []
            groups[path].append(node)

        for path, nodes in groups.items():
            if len(nodes) <= 1:
                continue

            # Sort to pick the best canonical node
            # Criteria 1: Depth (len of slugs_path) - shallowest first
            # Criteria 2: src_path == discovery_path (is it the actual location?)
            def canonical_sort_key(n: ContentNode):
                depth = len(n.slugs_path)
                # If it's a root-level course, depth is 0.
                # If it's a module inside a course, depth is 1.
                is_original = 0 if n.src_path == n.discovery_path else 1
                return (depth, is_original)

            nodes.sort(key=canonical_sort_key)
            canonical = nodes[0]

            for other in nodes[1:]:
                other.alias_to = canonical

    def _clean_name(self, name: str) -> str:
        cleaned = re.sub(r"^[\d]+[-_.\s]*", "", name)
        return cleaned.replace("-", " ").replace("_", " ") if cleaned else name

    def _process_slides_folder(
        self,
        course_node: ContentNode,
        slides_node: ContentNode,
        pre_processors: list[Processor],
        post_processors: list[Processor],
        global_config: dict | None = None,
        course_config: dict | None = None,
    ) -> None:
        """Process slides folder and generate slides.html."""
        slides = []
        
        # We need to process the files inside slides folder so they are written to output
        # Use a temporary list to avoid modification during iteration if that were an issue
        slide_children = [c for c in slides_node.children]
        
        for slide_file in slide_children:
            if slide_file.is_file and slide_file.file_extension == ".md":
                # Process the slide file to generate the actual slide HTML
                # This logic mimics _process_node but for slides specifically
                
                # Load content
                markdown = self.loader.load(slide_file.src_path)
                content = markdown["content"]
                metadata = markdown.get("metadata", {})
                slide_file.metadata = metadata
                
                # Apply processors
                for processor in pre_processors:
                    content = processor.execute(slide_file, content)
                
                # Ensure type is set to slide so render logic knows what to do
                metadata["type"] = "slide"
                
                # Render slide content
                if hasattr(self.markdown_renderer, "render_slide"):
                    content = self.markdown_renderer.render_slide(content)
                else:
                    content = self.markdown_renderer.render(content)

                render_config = (global_config or {}).copy()
                if course_config:
                    render_config.update(course_config)

                if hasattr(self.html_renderer, "render_slide"):
                    html = self.html_renderer.render_slide(
                        content, slide_file, metadata=metadata, config=render_config
                    )
                else:
                    html = self.html_renderer.render(
                        content, slide_file, metadata=metadata, config=render_config
                    )

                for processor in post_processors:
                    html = processor.execute(slide_file, html)

                # Write the slide file
                self.writer.write(slide_file, html)

                # Collect metadata for listing
                slide_name = self._clean_name(slide_file.name)
                if metadata.get("title"):
                    slide_name = metadata["title"]
                
                slides.append({
                    "name": slide_name,
                    "slug": slide_file.slug,
                })
            
            # Copy non-markdown files (images, etc)
            elif slide_file.is_file:
                self.writer.copy_file(slide_file)

        # Sort slides by numeric prefix if present
        def sort_key(s):
            match = re.search(r"^(\d+)", s["slug"])
            return int(match.group(1)) if match else 9999
        
        slides.sort(key=sort_key)
        
        # Render slides page
        render_config = (global_config or {}).copy()
        if course_config:
            render_config.update(course_config)
        
        slides_html = self.html_renderer.render_slides(
            course_node, slides, config=render_config
        )
        
        for processor in post_processors:
            slides_html = processor.execute(slides_node, slides_html)
        
        self.writer.write_slides(course_node, slides_html)

    def _process_node(
        self,
        node: ContentNode,
        pre_processors: list[Processor],
        post_processors: list[Processor],
        global_config: dict | None = None,
        parent_course_config: dict | None = None,
        existing_checksums: dict | None = None,
        new_checksums: dict | None = None,
    ) -> None:
        current_config = parent_course_config
        existing_checksums = existing_checksums or {}
        new_checksums = new_checksums if new_checksums is not None else {}

        # Check for config.yaml in this directory if it's a directory
        if not node.is_file and node.src_path:
            local_config_path = os.path.join(node.src_path, "config.yaml")
            if os.path.exists(local_config_path):
                local_config = ConfigLoader().load(local_config_path)
                # Merge with parent config or override? Usually override for specific fields.
                current_config = local_config

        if node.alias_to:
            print(f"Skipping alias: {node.slug} (points to {node.alias_to.slug})")
            return

        if node.is_file:
            if node.file_extension == ".md":
                markdown = self.loader.load(node.src_path)
                content = markdown["content"]

                current_checksum = hashlib.md5(content.encode("utf-8")).hexdigest()
                new_checksums[node.src_path] = current_checksum
                is_changed = existing_checksums.get(node.src_path) != current_checksum

                output_exists = True
                if hasattr(self.writer, "exists"):
                    output_exists = self.writer.exists(node)

                if not is_changed and output_exists:
                    print(f"Skipping unchanged: {node.slug}")
                    return

                metadata = markdown.get("metadata", {})
                node.metadata = metadata

                for processor in pre_processors:
                    content = processor.execute(node, content)

                chapter = None
                match = re.match(r"^(\d+)\s*[-_.\s]", node.name)
                if match:
                    chapter = int(match.group(1))

                render_config = (global_config or {}).copy()
                if current_config:
                    render_config.update(current_config)

                if metadata.get("type") == "slide":
                    # Render as Reveal.js slides
                    if hasattr(self.markdown_renderer, "render_slide"):
                        content = self.markdown_renderer.render_slide(content)
                    else:
                        # Fallback if method missing (should not happen with correct setup)
                        content = self.markdown_renderer.render(
                            content, chapter=chapter
                        )

                    if hasattr(self.html_renderer, "render_slide"):
                        html = self.html_renderer.render_slide(
                            content, node, metadata=metadata, config=render_config
                        )
                    else:
                        html = self.html_renderer.render(
                            content, node, metadata=metadata, config=render_config
                        )
                else:
                    # Standard page render
                    content = self.markdown_renderer.render(content, chapter=chapter)

                    html = self.html_renderer.render(
                        content, node, metadata=metadata, config=render_config
                    )

                for processor in post_processors:
                    html = processor.execute(node, html)

                self.writer.write(node, html)
            else:
                self.writer.copy_file(node)
        else:
            has_md_files = any(
                c.is_file and c.file_extension == ".md" for c in node.children
            )
            # Or has sub-courses?
            has_subcourses = any(
                not c.is_file
                and any(gc.is_file and gc.file_extension == ".md" for gc in c.children)
                for c in node.children
            )

            if (has_md_files or has_subcourses) and node.parent is not None:
                render_config = (global_config or {}).copy()
                if current_config:
                    render_config.update(current_config)

                contents_html = self.html_renderer.render_contents(
                    node, config=render_config
                )
                for processor in post_processors:
                    contents_html = processor.execute(node, contents_html)
                self.writer.write_contents(node, contents_html)

        for child in node.children:
            # Skip slides folder from normal processing
            if not child.is_file and child.name.lower() == "slides":
                continue
                
            self._process_node(
                child,
                pre_processors,
                post_processors,
                global_config,
                current_config,
                existing_checksums,
                new_checksums,
            )

        # Process slides folder separately if it exists
        if not node.is_file and node.parent is not None:
            for child in node.children:
                if not child.is_file and child.name.lower() == "slides":
                    # Check if slides folder has markdown files
                    has_md = any(
                        gc.is_file and gc.file_extension == ".md" for gc in child.children
                    )
                    if has_md:
                        self._process_slides_folder(
                            node, child, pre_processors, post_processors, global_config, current_config
                        )
                    break
