import os
import re
import mistune
import yaml
import base64
from pathlib import Path

# Default location of the bundled template config
_DEFAULT_TEMPLATE_CONFIG = Path(__file__).parent.parent.parent / "templates" / "exam_template.yaml"

class HTMLAssignmentExporter:
    def __init__(self, template_config=None):
        self.total_points = 0.0
        
        # Load template config from YAML
        config_path = Path(template_config) if template_config else _DEFAULT_TEMPLATE_CONFIG
        with open(config_path, "r", encoding="utf-8") as f:
            self._tpl = yaml.safe_load(f)

    def _process_points_and_content(self, markdown_content: str) -> tuple[float, str]:
        """Parse points from markdown, calculate total, and inject point labels with wrapping divs."""
        total = 0.0
        
        # Pattern: **N. [X.Y] Title** or **N. Title** or N. [X.Y] Title
        pattern = r'^(?:\*\*)?(\d+)\.\s*(?:([\[\(]\d+(?:[.,]\d+)?(?:\s*pontos?)?[\]\)]))?\s*(.*?)(?:\*\*|(?=\s*\n|$))'
        
        # Split content by where questions start to wrap them
        # Split content to check if there are any questions
        parts = re.split(pattern, markdown_content, flags=re.MULTILINE)
        
        if len(parts) <= 1:
            return total, markdown_content

        matches = list(re.finditer(pattern, markdown_content, flags=re.MULTILINE))
        processed = markdown_content[:matches[0].start()] if matches else markdown_content
        
        for i, match in enumerate(matches):
            q_num = match.group(1)
            pts_marker = match.group(2)
            q_text = match.group(3)
            
            if pts_marker:
                m_val = re.search(r'(\d+(?:[.,]\d+)?)', pts_marker)
                val = float(m_val.group(1).replace(',', '.')) if m_val else 1.0
            else:
                val = 1.0
            
            total += val
            val_str = f"{val:.1f}".replace('.', ',')
            suffix = "ponto" if val == 1.0 else "pontos"
            
            header = f"\n<div class=\"question\">\n\n**{q_num}. {q_text} ({val_str} {suffix})**"
            
            # Content of this question goes until next match or end of string
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(markdown_content)
            q_body = markdown_content[start:end]
            
            processed += header + q_body + "\n</div>\n"

        return total, processed

    def export(
        self,
        markdown_content: str,
        out_html_path: str,
        assignment_title: str | None = None,
        course_name: str | None = None,
        metadata: dict | None = None,
        assignment_type: str | None = None,
        html_renderer = None,  # Injected from the application layer
    ):
        """Export the assignment to a standalone HTML file."""
        if metadata is None: metadata = {}
        if assignment_title is None: assignment_title = metadata.get("title", "Avaliação")

        is_exam = (assignment_type == "exam")
        
        # Remove frontmatter from content if present
        markdown_content = re.sub(r'^---\n.*?\n---\n', '', markdown_content, flags=re.DOTALL)
        
        # Parse points and transform markdown
        self.total_points, transformed_markdown = self._process_points_and_content(markdown_content)

        # Basic context for the template
        tpl_cfg = self._tpl
        header_cfg = tpl_cfg.get("header_table", {})
        inst_cfg = tpl_cfg.get("institution", {})

        # Format total points
        fmt_total_points = ""
        if self.total_points > 0:
            fmt_total_points = f"{self.total_points:.1f}".replace('.', ',')
        else:
            meta_pts = metadata.get("points") or metadata.get("valor")
            if meta_pts is not None:
                fmt_total_points = f"{float(meta_pts):.1f}".replace('.', ',')

        # Determine course display name
        curso_name = metadata.get("course")
        if not curso_name:
            if course_name and "engenharia de software" in course_name.lower():
                curso_name = "Engenharia de Computação"
            else:
                curso_name = course_name or "Desconhecido"

        # Determine Date
        date_label = header_cfg.get("date_label", "Data" if is_exam else "Entrega")
        date_value = metadata.get("due_date") or metadata.get("date") or ""

        # Render markdown to HTML
        # In mistune v3+, hard_wrap is an option of the markdown object, not the renderer
        # We allow escape=False so our injected <div> tags are not escaped
        # In mistune v3+, we can allow raw HTML by not using the safe plugin or by setting escape=False in the HTML renderer
        # Since we want to keep the default renderer but allow our tags, we'll use a custom renderer if needed, 
        # but mistune.create_markdown(escape=False) is usually the way.
        markdown = mistune.create_markdown(plugins=["table"], escape=False, hard_wrap=True)
        body_html = markdown(transformed_markdown)

        # Get logo as base64
        logo_base64 = None
        logo_path = inst_cfg.get("logo")
        if logo_path:
            # Resolve relative to project root or absolute
            abs_logo_path = Path(logo_path)
            if not abs_logo_path.is_absolute():
                # Define possible base directories to search in
                base_dirs = [
                    Path(__file__).parent.parent.parent,           # src/course_forge
                    Path(__file__).parent.parent.parent / "templates", # src/course_forge/templates
                    Path.cwd(),                                    # Current working directory
                ]
                
                # If logo_path already starts with 'assets/', we should also try searching for the file 
                # inside those folders without the 'assets/' prefix if not found
                for base in base_dirs:
                    # Try direct join
                    test_path = base / logo_path
                    if test_path.exists():
                        abs_logo_path = test_path
                        break
                    
                    # Try without the first component if it's 'assets' or 'img'
                    parts = Path(logo_path).parts
                    if len(parts) > 1 and parts[0] in ['assets', 'img', 'images']:
                        test_path = base / Path(*parts[1:])
                        if test_path.exists():
                            abs_logo_path = test_path
                            break
                        
                        # Try searching specifically in an 'assets' or 'img' subfolder of base
                        for sub in ['assets', 'img', 'images']:
                            test_path = base / sub / Path(*parts[1:])
                            if test_path.exists():
                                abs_logo_path = test_path
                                break
                        if abs_logo_path.exists(): break

            if abs_logo_path.exists():
                try:
                    with open(abs_logo_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        ext = abs_logo_path.suffix.lower()
                        mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                        logo_base64 = f"data:{mime_type};base64,{encoded_string}"
                except Exception as e:
                    print(f"Warning: Could not encode logo: {e}")

        # Use the injected HTML renderer to build the final page
        # This allows us to reuse the Jinja2 setup and base_url logic
        if html_renderer and hasattr(html_renderer, "render_assignment"):
            final_html = html_renderer.render_assignment(
                content=body_html,
                assignment_title=assignment_title,
                course_name=course_name,
                course_display_name=curso_name,
                discipline_name=course_name,
                professor_name=inst_cfg.get("professor", "Gabriel Soares Baptista"),
                date_label=date_label,
                date_value=date_value,
                total_points=fmt_total_points,
                is_exam=is_exam,
                instructions=tpl_cfg.get("instructions") if is_exam else None,
                logo_url=logo_base64 or logo_path,
                metadata=metadata
            )
        else:
            # Fallback if no renderer injected (simpler template approach)
            final_html = f"<html><body>{body_html}</body></html>"

        return final_html
