import minify_html  # type: ignore

from course_forge.domain.entities import ContentNode

from .base import Processor


class HTMLMinifyProcessor(Processor):
    def execute(self, node: ContentNode, content: str) -> str:
        try:
            minified = minify_html.minify(
                content,
                minify_js=True,
                minify_css=True,
                remove_processing_instructions=True,
                keep_closing_tags=True,  # Ensure closing tags are kept to avoid structural issues
            )

            # Safeguard: Check for truncation by verifying closing tags
            # If input has </html> but output doesn't, we definitely lost content at the end.
            if "</html>" in content and "</html>" not in minified:
                print(
                    f"Warning: HTML minification truncated result for node {node.slug} (missing </html>). Using original content."
                )
                return content

            # Additional heuristic: check for </body> if </html> isn't present in input (fragments)
            if "</body>" in content and "</body>" not in minified:
                print(
                    f"Warning: HTML minification truncated result for node {node.slug} (missing </body>). Using original content."
                )
                return content

            # Safeguard: If minification results in suspicious data loss (e.g. empty string or extreme reduction)
            # < 1% of original size is very suspicious
            if len(minified) < len(content) * 0.01 and len(content) > 0:
                print(
                    f"Warning: HTML minification resulted in suspicious size reduction for node {node.slug}. Using original content."
                )
                return content

            return minified
        except Exception as e:
            print(
                f"Warning: HTML minification failed for node {node.slug}: {e}. Using original content."
            )
            return content
