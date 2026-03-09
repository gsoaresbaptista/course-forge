import os
import subprocess
import mistune
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_COLOR_INDEX
import re

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.token import Token
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

# Callout type -> (label, border hex color)
CALLOUT_STYLES = {
    "important": ("⚠ Importante",  "E57C00"),
    "warning":   ("⚠ Atenção",     "D32F2F"),
    "danger":    ("✖ Perigo",      "B71C1C"),
    "note":      ("ℹ Nota",        "1976D2"),
    "tip":       ("✔ Dica",        "2E7D32"),
    "info":      ("ℹ Info",        "0288D1"),
}

# Pygments token -> (bold, italic, hex_rgb or None)
_PYGMENTS_TOKEN_STYLE = {
    Token.Keyword:            (True,  False, "0000CC"),
    Token.Keyword.Type:       (True,  False, "0000CC"),
    Token.Name.Builtin:       (True,  False, "0000CC"),
    Token.Name.Function:      (False, False, "0000AA"),
    Token.Name.Class:         (True,  False, "006600"),
    Token.Comment:            (False, True,  "888888"),
    Token.Comment.Single:     (False, True,  "888888"),
    Token.Comment.Multiline:  (False, True,  "888888"),
    Token.Literal.String:     (False, False, "CC0000"),
    Token.Literal.String.Doc: (False, True,  "880000"),
    Token.Literal.Number:     (False, False, "AA00AA"),
    Token.Operator:           (False, False, "555555"),
    Token.Operator.Word:      (True,  False, "0000CC"),
    Token.Punctuation:        (False, False, "333333"),
    Token.Generic.Heading:    (True,  False, "000080"),
}

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

class AssignmentExporter:
    def __init__(self, template_path="/home/gabriel/Downloads/FA-DIF-005 - MODELO DE PROVA 2026-1 - ENGENHARIAS.docx"):
        self.template_path = template_path
        self.total_points = 0.0
        self.out_dir = ""

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _add_left_border(self, paragraph, hex_color):
        """Add a colored left border to a paragraph."""
        pPr = paragraph._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        left = OxmlElement('w:left')
        left.set(qn('w:val'), 'single')
        left.set(qn('w:sz'), '24')   # 3pt line
        left.set(qn('w:space'), '4')
        left.set(qn('w:color'), hex_color)
        pBdr.append(left)
        pPr.append(pBdr)

    def _add_shading(self, paragraph, hex_color):
        """Add a light background shading."""
        # Lighten the border colour by mixing with white at 85%
        r, g, b = self._hex_to_rgb(hex_color)
        lr = int(r * 0.15 + 255 * 0.85)
        lg = int(g * 0.15 + 255 * 0.85)
        lb = int(b * 0.15 + 255 * 0.85)
        fill = f"{lr:02X}{lg:02X}{lb:02X}"
        pPr = paragraph._p.get_or_add_pPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill)
        pPr.append(shd)

    def _delete_paragraph(self, paragraph):
        p = paragraph._element
        p.getparent().remove(p)
        paragraph._p = paragraph._element = None

    def _add_runs(self, paragraph, children):
        for child in children:
            child_type = child.get("type")
            if child_type == "text":
                text = child.get("raw", child.get("text", ""))
                run = paragraph.add_run(text)
                run.font.name = "Arial"
                run.font.size = Pt(10)
            elif child_type == "softbreak":
                # Handled by chunking now, but fallback to space
                run = paragraph.add_run(" ")
                run.font.name = "Arial"
                run.font.size = Pt(10)
            elif child_type == "strong":
                full_text = "".join(grand.get("raw", grand.get("text", "")) for grand in child.get("children", []))
                
                # Look for explicit points: "**1. [1.5] Avalie...**" or "**1. (2,0 pontos) ...**"
                match = re.search(r'^(\d+)\.\s*(?:\[|\()(\d+(?:[.,]\d+)?)(?:\s*pontos?)?(?:\]|\))\s*(.*)', full_text, flags=re.IGNORECASE)
                if match:
                    num = match.group(1)
                    pts = match.group(2).replace('.', ',')
                    rest = match.group(3)
                    try:
                        self.total_points += float(pts.replace(',', '.'))
                    except ValueError:
                        pass
                else:
                    match = re.search(r'^(\d+)\.\s*(.*)', full_text)
                    if match:
                        num = match.group(1)
                        pts = "1,0"
                        rest = match.group(2)
                        self.total_points += 1.0
                    else:
                        num = None
                        
                if num is not None:
                    try:
                        val = float(pts.replace(',', '.'))
                    except ValueError:
                        val = 1.0
                    label_ponto = "ponto" if val == 1.0 else "pontos"
                    run = paragraph.add_run(f"Questão {num:0>2} ({pts} {label_ponto}): ")
                    run.font.name = "Arial"
                    run.font.size = Pt(10)
                    run.bold = True
                    if rest:
                        run = paragraph.add_run(rest)
                        run.font.name = "Arial"
                        run.font.size = Pt(10)
                        run.bold = True
                else:
                    run = paragraph.add_run(full_text)
                    run.font.name = "Arial"
                    run.font.size = Pt(10)
                    run.bold = True
            elif child_type == "emphasis":
                for grand in child.get("children", []):
                    run = paragraph.add_run(grand.get("raw", grand.get("text", "")))
                    run.font.name = "Arial"
                    run.font.size = Pt(10)
                    run.italic = True
            elif child_type == "codespan":
                # codespan is a leaf: raw holds the code text directly
                raw_code = child.get("raw", child.get("text", ""))
                if not raw_code and child.get("children"):
                    raw_code = "".join(c.get("raw", c.get("text", "")) for c in child["children"])
                run = paragraph.add_run(raw_code)
                run.font.name = "Courier New"
                run.font.size = Pt(10)
            elif child_type == "link":
                self._add_runs(paragraph, child.get("children", []))
            elif child_type == "image":
                src = child.get("dest", child.get("src", ""))
                # Remove query params (like filename?raw=true)
                src = src.split('?')[0]
                # Embed image
                src_abs = os.path.join(self.out_dir, src)
                if src_abs.endswith('.svg') and os.path.exists(src_abs):
                    png_path = src_abs + ".png"
                    try:
                        subprocess.run(["convert", src_abs, png_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        src_abs = png_path
                    except Exception as e:
                        print("Failed to convert SVG to PNG:", e)
                
                if os.path.exists(src_abs):
                    run = paragraph.add_run()
                    try:
                        # Add picture with reasonable width
                        run.add_picture(src_abs, width=Inches(5.0))
                    except Exception as e:
                        print(f"Failed to add picture {src_abs}:", e)
                else:
                    paragraph.add_run("[Image: " + child.get("alt", "") + "]")
            elif "children" in child:
                self._add_runs(paragraph, child["children"])

    def _render_node(self, node, doc, list_level=0, callout_style=None):
        ntype = node.get("type")
        
        if ntype == "heading":
            level = node.get("attrs", {}).get("level", 1)
            p = doc.add_paragraph()
            p.style = "Normal"
            if callout_style:
                self._add_left_border(p, callout_style)
                self._add_shading(p, callout_style)
            self._add_runs(p, node.get("children", []))
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(16 - level)

        elif ntype == "paragraph":
            chunks = []
            current_chunk = []
            for child in node.get("children", []):
                if child.get("type") == "softbreak":
                    chunks.append(current_chunk)
                    current_chunk = []
                else:
                    current_chunk.append(child)
            if current_chunk:
                chunks.append(current_chunk)
                
            for chunk in chunks:
                if not chunk: continue
                p = doc.add_paragraph()
                try:
                    p.style = "List Paragraph" if list_level > 0 else "Normal"
                except KeyError:
                    p.style = "Normal"
                
                # Check if this paragraph contains options to apply right styles
                is_option = False
                is_question = False
                for child in chunk:
                    if child.get("type") == "text":
                        text = child.get("raw", child.get("text", ""))
                        if re.match(r'^[a-e]\)', text.strip()):
                            is_option = True
                    elif child.get("type") == "strong":
                        full_text = "".join(grand.get("raw", grand.get("text", "")) for grand in child.get("children", []))
                        if re.search(r'^(\d+)\.\s+', full_text):
                            is_question = True
                            
                if is_option:
                    try: p.style = "Body Text" 
                    except: pass
                    p.paragraph_format.left_indent = Pt(14.2)  # around 0.5cm
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                else:
                    p.paragraph_format.space_after = Pt(6)
                    if is_question:
                        p.paragraph_format.space_before = Pt(18)
                        p.paragraph_format.keep_with_next = True
                    else:
                        p.paragraph_format.space_before = Pt(0)
    
                self._add_runs(p, chunk)

        elif ntype == "block_quote":
            callout_type = None
            title_nodes = []
            body_from_first_p = []
            
            children = node.get("children", [])
            if children and children[0].get("type") == "paragraph":
                p1_children = children[0].get("children", [])
                
                # 1. Identify if it's a callout and find marker end
                full_text_until_bracket = ""
                marker_node_idx = -1
                for i, c in enumerate(p1_children):
                    if c.get("type") == "text":
                        txt = c.get("raw", c.get("text", ""))
                        full_text_until_bracket += txt
                        if "]" in full_text_until_bracket:
                            marker_node_idx = i
                            break
                    elif c.get("type") == "softbreak": break
                    else: break
                
                marker_match = re.match(r'^\[!(\w+)\]', full_text_until_bracket)
                if marker_match:
                    callout_type = marker_match.group(1).lower()
                    
                    # 2. Split first paragraph into title line and body lines
                    softbreak_idx = -1
                    for i, c in enumerate(p1_children):
                        if c.get("type") == "softbreak":
                            softbreak_idx = i
                            break
                    
                    raw_title_nodes = p1_children[:softbreak_idx] if softbreak_idx != -1 else p1_children
                    body_from_first_p = p1_children[softbreak_idx+1:] if softbreak_idx != -1 else []
                    
                    # 3. Create stripped title nodes (copy to avoid mutating original AST)
                    # We need to remove "[!type] " from the beginning of the text nodes
                    import copy
                    title_nodes = copy.deepcopy(raw_title_nodes)
                    
                    marker_full_str = marker_match.group(0) # e.g. "[!warning]"
                    to_strip = len(marker_full_str)
                    
                    # Strip from the start of title_nodes
                    curr_idx = 0
                    while to_strip > 0 and curr_idx < len(title_nodes):
                        node_to_edit = title_nodes[curr_idx]
                        if node_to_edit.get("type") == "text":
                            node_text = node_to_edit.get("raw", node_to_edit.get("text", ""))
                            strip_now = min(len(node_text), to_strip)
                            new_text = node_text[strip_now:]
                            node_to_edit["raw"] = new_text
                            if "text" in node_to_edit: node_to_edit["text"] = new_text
                            to_strip -= strip_now
                        curr_idx += 1
                    
                    # If after marker there's a space, strip it too
                    if title_nodes and title_nodes[0].get("type") == "text":
                        t = title_nodes[0].get("raw", "")
                        title_nodes[0]["raw"] = t.lstrip()
                        if "text" in title_nodes[0]: title_nodes[0]["text"] = t.lstrip()

            label_info = CALLOUT_STYLES.get(callout_type)
            if label_info:
                label, border_hex = label_info
                # Title paragraph
                title_p = doc.add_paragraph()
                title_p.style = "Normal"
                title_p.paragraph_format.space_after = Pt(2)
                title_p.paragraph_format.space_before = Pt(6)
                title_p.paragraph_format.left_indent = Pt(12)
                self._add_left_border(title_p, border_hex)
                self._add_shading(title_p, border_hex)
                
                r = title_p.add_run(f"{label}")
                r.bold = True
                r.font.name = "Arial"
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(*self._hex_to_rgb(border_hex))
                
                if title_nodes:
                    title_p.add_run(" — ").bold = True
                    # Use _add_runs but we MUST ensure they are bold and correct color
                    start_runs_idx = len(title_p.runs)
                    self._add_runs(title_p, title_nodes)
                    for r in title_p.runs[start_runs_idx:]:
                        r.bold = True
                        r.font.name = "Arial"
                        r.font.size = Pt(10)
                        r.font.color.rgb = RGBColor(*self._hex_to_rgb(border_hex))

                # Body items
                if body_from_first_p:
                    bp = doc.add_paragraph()
                    bp.style = "Normal"
                    bp.paragraph_format.left_indent = Pt(12)
                    self._add_left_border(bp, border_hex)
                    self._add_shading(bp, border_hex)
                    self._add_runs(bp, body_from_first_p)
                
                for child in children[1:]:
                    self._render_node(child, doc, list_level, callout_style=border_hex)
                
                # Closing spacer
                sp = doc.add_paragraph()
                sp.paragraph_format.space_after = Pt(4)
                sp.paragraph_format.space_before = Pt(0)
            else:
                # Plain blockquote or failed callout detection
                border_hex = "999999"
                for child in children:
                    self._render_node(child, doc, list_level, callout_style=border_hex)

        elif ntype == "list":
            # For lists we map options slightly differently if they're a,b,c etc.
            is_ordered = node.get("attrs", {}).get("ordered", False)
            for idx, child in enumerate(node.get("children", [])):
                if child.get("type") == "list_item":
                    p = doc.add_paragraph()
                    if callout_style:
                        self._add_left_border(p, callout_style)
                        self._add_shading(p, callout_style)
                    
                    try:
                        # ...
                        p.style = "List Bullet" if not is_ordered else "List Number"
                    except KeyError:
                        p.style = "Normal"
                        p.paragraph_format.left_indent = Pt(list_level * 20 + 20 + (12 if callout_style else 0))
                        p.add_run("• ")
                    for grand in child.get("children", []):
                        if grand.get("type") == "block_text":
                            self._add_runs(p, grand.get("children", []))
                        else:
                            self._render_node(grand, doc, list_level + 1, callout_style=callout_style)

        elif ntype == "block_code":
            lang = node.get("attrs", {}).get("info", "") or ""
            code = node.get("raw", node.get("text", "")).rstrip("\n")

            def _shaded_para():
                cp = doc.add_paragraph()
                if callout_style:
                    self._add_left_border(cp, callout_style)
                    self._add_shading(cp, callout_style)
                
                cp.style = "Normal"
                cp.paragraph_format.space_after = Pt(0)
                cp.paragraph_format.space_before = Pt(0)
                # If inside callout, add more indent
                base_indent = 12 if callout_style else 0
                cp.paragraph_format.left_indent = Pt(base_indent + 8)
                
                shd = OxmlElement('w:shd')
                shd.set(qn('w:fill'), 'F0F0F0')
                cp._p.get_or_add_pPr().append(shd)
                
                bdr = OxmlElement('w:pBdr')
                for side in ('top', 'left', 'bottom', 'right'):
                    el = OxmlElement(f'w:{side}')
                    el.set(qn('w:val'), 'single')
                    el.set(qn('w:sz'), '4')
                    el.set(qn('w:space'), '1')
                    el.set(qn('w:color'), 'CCCCCC')
                    bdr.append(el)
                cp._p.get_or_add_pPr().append(bdr)
                return cp

            if HAS_PYGMENTS and lang:
                try:
                    lexer = get_lexer_by_name(lang, stripall=True)
                except Exception:
                    lexer = None # Ensure lexer is None on exception
                if lexer:
                    # Tokenize and split into lines properly
                    lines = [[]]
                    for ttype, value in lexer.get_tokens(code):
                        parts = value.split('\n')
                        for i, part in enumerate(parts):
                            if part:
                                lines[-1].append((ttype, part))
                            if i < len(parts) - 1:
                                lines.append([])
                    
                    # Remove trailing empty line if it resulted from a final \n
                    if lines and not lines[-1]:
                        lines.pop()

                    for i, line_tokens in enumerate(lines):
                        lp = _shaded_para()
                        if i == len(lines) - 1:
                            lp.paragraph_format.space_after = Pt(6)
                        for ttype, val in line_tokens:
                            run = lp.add_run(val)
                            run.font.name = "Courier New"
                            run.font.size = Pt(9)
                            # Style resolution
                            style = None
                            tt = ttype
                            while tt:
                                style = _PYGMENTS_TOKEN_STYLE.get(tt)
                                if style: break
                                tt = tt.parent if hasattr(tt, 'parent') else None
                            if style:
                                b, it, h = style
                                run.bold, run.italic = b, it
                                if h: run.font.color.rgb = RGBColor(*self._hex_to_rgb(h))
                    return
            return

            # Fallback: plain monospace, one paragraph per line
            last_lp = None
            for line in code.split('\n'):
                last_lp = _shaded_para()
                r = last_lp.add_run(line)
                r.font.name = "Courier New"
                r.font.size = Pt(9)
            if last_lp is not None:
                last_lp.paragraph_format.space_after = Pt(6)

        elif ntype == "thematic_break":
            # Just ignore thematic break in assignments
            pass

        elif ntype == "table":
            children = node.get("children", [])
            head = next((c for c in children if c.get("type") == "table_head"), None)
            body = next((c for c in children if c.get("type") == "table_body"), None)

            head_rows = head.get("children", []) if head else []
            body_rows_raw = body.get("children", []) if body else []

            # body children may be table_row nodes directly or wrapped
            body_rows = []
            for item in body_rows_raw:
                if item.get("type") == "table_row":
                    body_rows.append(item.get("children", []))  # list of table_cell
                else:
                    body_rows.append([item])  # fallback

            header_cells_rows = []
            for hr in head_rows:
                if hr.get("type") in ("table_row", "table_head"):
                    header_cells_rows.append(hr.get("children", []))
                else:
                    # mistune wraps the head differently: head node IS the single row of cells
                    header_cells_rows.append(head_rows)
                    break

            all_row_cells = header_cells_rows + body_rows
            if not all_row_cells:
                pass
            else:
                cols = max(len(r) for r in all_row_cells)
                n_header = len(header_cells_rows)
                table = doc.add_table(rows=len(all_row_cells), cols=cols)
                try: table.style = 'Table Grid'
                except: pass
                for r_idx, cells in enumerate(all_row_cells):
                    is_header_row = r_idx < n_header
                    for c_idx, cell in enumerate(cells):
                        if c_idx >= cols:
                            continue
                        cell_p = table.rows[r_idx].cells[c_idx].paragraphs[0]
                        cell_p.paragraph_format.space_after = Pt(2)
                        cell_p.paragraph_format.space_before = Pt(2)
                        
                        # Tables inside callouts are tricky because cells can't easily have 
                        # half-borders and shading without messing up the table's own.
                        # Usually, if a table is inside a callout, we just let it be.
                        # But we could at least indent the table? 
                        # python-docx doesn't support table indentation easily via this API.
                        
                        if is_header_row:
                            tc = table.rows[r_idx].cells[c_idx]._tc
                            tcPr = tc.get_or_add_tcPr()
                            shd = OxmlElement('w:shd')
                            shd.set(qn('w:val'), 'clear')
                            shd.set(qn('w:color'), 'auto')
                            shd.set(qn('w:fill'), 'D9D9D9')
                            tcPr.append(shd)
                        
                        cell_children = cell.get("children", [])
                        self._add_runs(cell_p, cell_children)
                        if is_header_row:
                            for run in cell_p.runs:
                                run.bold = True

        else:
            for child in node.get("children", []):
                self._render_node(child, doc, list_level)

    def export(self, markdown_content: str, out_docx_path: str, out_pdf_path: str, assignment_title="Avaliação", course_name="", metadata=None, assignment_type="assignment"):
        if metadata is None: metadata = {}
        if not os.path.exists(self.template_path):
            print(f"Template path {self.template_path} not found. Using an empty document.")
            doc = Document()
        else:
            doc = Document(self.template_path)

        self.out_dir = os.path.dirname(out_docx_path)
        self.total_points = 0.0

        is_exam = (assignment_type == "exam")
                            
        for i, p in reversed(list(enumerate(doc.paragraphs))):
            if i >= 3:
                self._delete_paragraph(p)
                
        if doc.tables and not is_exam:
            # Remove instructions table early before doc.tables updates
            if len(doc.tables) > 1:
                t1 = doc.tables[1]
                t1._element.getparent().remove(t1._element)
            
            table = doc.tables[0]
            try:
                tr = table.rows[2]._tr
                tr.getparent().remove(tr)
            except Exception:
                pass
            
            try:
                table.rows[1].cells[2].text = "Valor:"
            except Exception:
                pass

        title_p = doc.add_paragraph()
        title_p.style = "Normal"
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_p.add_run(assignment_title.upper())
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(12)
        
        doc.add_paragraph() # spacing

        markdown_content = re.sub(r'^---\n.*?\n---\n', '', markdown_content, flags=re.DOTALL)

        m = mistune.create_markdown(renderer=None, plugins=["table"])
        ast = m(markdown_content)
        
        for node in ast:
            self._render_node(node, doc)
            
        curso_name = metadata.get("course")
        if not curso_name:
            if "engenharia de software" in course_name.lower():
                curso_name = "Engenharia de Computação"
            else:
                curso_name = course_name
            
        if doc.tables:
            table = doc.tables[0]
            visited_cells = set()
            for row in table.rows:
                for cell in row.cells:
                    if cell in visited_cells:
                        continue
                    visited_cells.add(cell)
                    for paragraph in cell.paragraphs:
                        text = paragraph.text
                        if "Curso:" in text and curso_name and f"Curso: {curso_name}" not in text:
                            paragraph.text = text.replace("Curso:", f"Curso: {curso_name}")
                        elif "Disciplina:" in text and course_name and f"Disciplina: {course_name}" not in text:
                            paragraph.text = text.replace("Disciplina:", f"Disciplina: {course_name}")
                        elif "Professor(a):" in text and "Gabriel" not in text:
                            paragraph.text = text.replace("Professor(a):", "Professor(a): Gabriel Soares Baptista")
                        elif "Valor:" in text:
                            fmt_val = str(self.total_points).replace('.', ',')
                            if fmt_val.endswith(',0'):
                                fmt_val = fmt_val[:-2] # 2,0 -> 2
                            paragraph.text = text.replace("Valor:", f"Valor: {fmt_val}")
                            
        doc.save(out_docx_path)
        
        try:
            cmd = f'libreoffice --headless --convert-to pdf "{out_docx_path}" --outdir "{self.out_dir}" > /dev/null 2>&1'
            os.system(cmd)
        except Exception as e:
            print("Failed to convert to PDF via libreoffice", e)
