import hashlib
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from course_forge.application.loaders import MarkdownLoader
from course_forge.application.processors import Processor
from course_forge.application.renders import HTMLTemplateRenderer, MarkdownRenderer
from course_forge.application.services.build_cache import BuildCache
from course_forge.application.writers import OutputWriter
from course_forge.config import Config
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
        self.assignment_exporter = None
        self.slide_urls = []
        self._slides_lock = threading.Lock()
        self.cache = None

    def execute(
        self,
        root_path: str,
        pre_processors: list[Processor],
        post_processors: list[Processor],
        template_dir: str | None = None,
    ) -> None:
        cache_dir = os.path.join(root_path, ".course_forge_cache")
        self.cache = BuildCache(cache_dir)

        config_path = os.path.join(root_path, "config.yaml")
        config = ConfigLoader().load(config_path)

        # Inject config into html_renderer if supported
        if hasattr(self.html_renderer, "config"):
            self.html_renderer.config = config

        tree = self.repository.load(root_path)

        if Config.course_filter:
            # Filter children of root node to only include the requested course
            filtered_children = []
            for child in tree.root.children:
                if not child.is_file and child.slug == Config.course_filter:
                    filtered_children.append(child)
                elif not child.is_file and child.name == Config.course_filter:
                    filtered_children.append(child)
            
            if not filtered_children:
                print(f"Warning: Course '{Config.course_filter}' not found.")
            else:
                tree.root.children = filtered_children
                print(f"Filtering build to course: {Config.course_filter}")

        self._detect_aliases(tree.root)

        # Inject root node into processors that need it
        for processor in pre_processors + post_processors:
            if hasattr(processor, "set_root"):
                processor.set_root(tree.root)

        self.writer.copy_assets(self.html_renderer.template_dir, skip_bundled=False)

        with ThreadPoolExecutor() as executor:
            futures = []
            self._process_node(
                tree.root,
                pre_processors,
                post_processors,
                global_config=config,
                parent_course_config=None,
                executor=executor,
                futures=futures,
            )
            for f in as_completed(futures):
                f.result()

        courses = self._collect_top_level_courses(tree.root)

        if courses:
            if Config.course_filter and os.path.exists(os.path.join(self.writer._root_path, "index.html")):
                print(f"Skipping main index.html update because we are filtering by course '{Config.course_filter}'.")
            else:
                index_html = self.html_renderer.render_index(courses)
                for processor in post_processors:
                    index_html = processor.execute(tree.root, index_html)
                self.writer.write_index(index_html)

        if Config.export_slides:
            # Check if any slide was actually collected
            if not self.slide_urls:
                # If we filtered by course, maybe we didn't collect any slide URLs because they were skipped by cache
                # But my _process_node should handle it.
                pass
                
            print("Exporting slides to PDF...")
            from course_forge.infrastructure.services.chrome_pdf_exporter import ChromePdfExporter
            from course_forge.infrastructure.services.decktape_exporter import DeckTapeExporter
            
            # Sort URLs for consistent output
            with self._slides_lock:
                urls = sorted(list(set(self.slide_urls)))
            
            if urls:
                # Prefer DeckTape for Reveal.js as it iterates through slides
                # and handles fragments better than a simple Chrome print.
                import shutil
                if shutil.which("node"):
                    print("Using DeckTape for high-quality slide export (Node.js detected)")
                    exporter = DeckTapeExporter(self.writer._root_path)
                    exporter.export_slides(urls)
                else:
                    # Fallback to Chrome if Node is missing
                    chrome_exporter = ChromePdfExporter(self.writer._root_path)
                    if chrome_exporter.chrome_path:
                        print(f"Using Chrome for PDF export ({chrome_exporter.chrome_path})")
                        chrome_exporter.export_slides(urls)
                    else:
                        print("Neither Node.js nor Chrome found. Slide export failed.")
            else:
                print("No slides found for export.")
        
        # Save cache
        self.cache.save()

    def _collect_top_level_courses(self, node: ContentNode) -> list[dict]:
        courses = []
        # We only want direct children of root that are courses
        for child in node.children:
            course_name = self._clean_name(child.name)

            # Check for config.yaml to get custom name and visibility
            if not child.is_file and child.src_path:
                # Never index 'assignments' or 'slides' as top-level courses
                if child.name.lower() in ["assignments", "slides"]:
                    continue

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
                
                # Incremental Build check
                out_path = self.writer.get_output_path(slide_file)
                if not Config.debug and not self.cache.has_changed(slide_file.src_path) and os.path.exists(out_path):
                    # Collect URL for export
                    with self._slides_lock:
                        rel_path = "/".join(slide_file.slugs_path + [slide_file.slug + ".html"])
                        self.slide_urls.append(rel_path)

                    slide_name = self._clean_name(slide_file.name)
                    if metadata.get("title"):
                        slide_name = metadata["title"]
                    
                    slides.append({
                        "name": slide_name,
                        "slug": slide_file.slug,
                    })
                    continue

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
                self.cache.update(slide_file.src_path)

                # Collect URL for export
                with self._slides_lock:
                    rel_path = "/".join(slide_file.slugs_path + [slide_file.slug + ".html"])
                    self.slide_urls.append(rel_path)

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
                out_path = self.writer.get_output_path(slide_file)
                if not Config.debug and not self.cache.has_changed(slide_file.src_path) and os.path.exists(out_path):
                    continue
                self.writer.copy_file(slide_file)
                self.cache.update(slide_file.src_path)

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
        executor=None,
        futures=None,
    ) -> None:
        current_config = parent_course_config

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

        def process_file():
            if node.file_extension == ".md":
                markdown = self.loader.load(node.src_path)
                content = markdown["content"]

                metadata = markdown.get("metadata", {})
                node.metadata = metadata

                # Incremental Build check
                out_path = self.writer.get_output_path(node)
                if not Config.debug and not self.cache.has_changed(node.src_path) and os.path.exists(out_path):
                    # Still need to collect slide URLs if we are exporting
                    if metadata.get("type") == "slide":
                        with self._slides_lock:
                            rel_path = "/".join(node.slugs_path + [node.slug + ".html"])
                            self.slide_urls.append(rel_path)
                    return

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
                elif metadata.get("type") in ["assignment", "exam"]:
                    if not Config.generate_exams:
                        html = None
                    else:
                        out_dir = os.path.join(self.writer._root_path, *node.slugs_path)
                        out_html_path = os.path.join(out_dir, node.slug + ".html")
                        
                        if not Config.debug and not self.cache.has_changed(node.src_path) and os.path.exists(out_html_path):
                            html = None
                        else:
                            original_markdown = content
                            
                            # Also render for normal site view if needed, but primarily we want the assignment export
                            rendered_body = self.markdown_renderer.render(content, chapter=chapter)
                            
                            if self.assignment_exporter:
                                os.makedirs(out_dir, exist_ok=True)
                                course_name = render_config.get("name", "Unknown Course")
                                assignment_title = metadata.get("title", "Avaliação")
                                assignment_type = metadata.get("type")
                                
                                # Get standalone HTML
                                html = self.assignment_exporter.export(
                                    original_markdown, 
                                    out_html_path, 
                                    assignment_title=assignment_title, 
                                    course_name=course_name, 
                                    metadata=metadata,
                                    assignment_type=assignment_type,
                                    html_renderer=self.html_renderer
                                )
                                
                                # Run post-processors (like asset bundling) on the standalone HTML
                                for processor in post_processors:
                                    html = processor.execute(node, html)
                                
                                # Write the final processed HTML to the assignment path
                                with open(out_html_path, "w", encoding="utf-8") as f:
                                    f.write(html)
                                
                                self.cache.update(node.src_path)
                                
                                # Prevent normal write from use case (we already wrote it)
                                html = None 
                    
                else:
                    # Check if it was placed inside 'assignments' folder but missing metadata
                    is_in_assignments = False
                    p = node.parent
                    while p:
                        if p.name.lower() == "assignments":
                            is_in_assignments = True
                            break
                        p = p.parent
                        
                    if is_in_assignments:
                        if Config.generate_exams:
                            print(f"WARNING: File {node.src_path} in assignments folder is not marked as assignment or exam. Skipping HTML/DOCX/PDF generation.")
                        html = None
                    else:
                        # Standard page render
                        content = self.markdown_renderer.render(content, chapter=chapter)
    
                        html = self.html_renderer.render(
                            content, node, metadata=metadata, config=render_config
                        )

                if html is not None:
                    for processor in post_processors:
                        html = processor.execute(node, html)
    
                    # Assignments and exams are exported as DOCX/PDF only; skip HTML page.
                    if metadata.get("type") not in ["assignment", "exam"]:
                        self.writer.write(node, html)
                        self.cache.update(node.src_path)
                        
                        if metadata.get("type") == "slide":
                            with self._slides_lock:
                                rel_path = "/".join(node.slugs_path + [node.slug + ".html"])
                                self.slide_urls.append(rel_path)
            else:
                out_path = self.writer.get_output_path(node)
                if not Config.debug and not self.cache.has_changed(node.src_path) and os.path.exists(out_path):
                    return
                self.writer.copy_file(node)
                self.cache.update(node.src_path)

        def process_dir():
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
                is_in_assignments = False
                p = node
                while p:
                    if p.name.lower() == "assignments":
                        is_in_assignments = True
                        break
                    p = p.parent
                    
                if not is_in_assignments or Config.generate_exams:
                    render_config = (global_config or {}).copy()
                    if current_config:
                        render_config.update(current_config)
    
                    contents_html = self.html_renderer.render_contents(
                        node, config=render_config
                    )
                    for processor in post_processors:
                        contents_html = processor.execute(node, contents_html)
                    self.writer.write_contents(node, contents_html)

        if node.is_file:
            if executor is not None and futures is not None:
                futures.append(executor.submit(process_file))
            else:
                process_file()
        else:
            if executor is not None and futures is not None:
                futures.append(executor.submit(process_dir))
            else:
                process_dir()

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
                executor,
                futures,
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
                        def process_slides():
                            self._process_slides_folder(
                                node, child, pre_processors, post_processors, global_config, current_config
                            )
                        if executor is not None and futures is not None:
                            futures.append(executor.submit(process_slides))
                        else:
                            process_slides()
                    break
