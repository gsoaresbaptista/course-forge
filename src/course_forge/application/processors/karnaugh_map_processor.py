import re
import schemdraw
from schemdraw import logic, Drawing
import itertools
from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase

class KarnaughMapProcessor(SVGProcessorBase):
    """Processor for Karnaugh Maps (K-Map).
    
    Syntax:
        ```karnaugh.map centered
        names: AB
        grid:
          0 1
          1 0
        ```
    """

    pattern = SVGProcessorBase.create_pattern("karnaugh.map", r"(?P<code>.*?)")

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            code = match.group("code").strip()
            attrs = self.parse_svg_attributes(match)

            try:
                config = self._parse_config(code)
                svg_data = self._render_kmap(config)
                
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph kmap-img",
                )
                svg_html = f'<div class="no-break">{svg_html}</div>'
                content = content.replace(match.group(0), svg_html)
            except Exception as e:
                error_msg = f'<div class="error">K-Map error: {str(e)}</div>'
                content = content.replace(match.group(0), error_msg)

        return content

    def _parse_config(self, code: str) -> dict:
        config = {
            "names": "",
            "outputs": "",
            "schemdraw_names": "", # Permuted names for schemdraw
            "groups": {}, # Dict for schemdraw (key=cells, val=style)
            "truthtable": [],
        }
        
        lines = code.strip().split("\n")
        
        # Phase 1: Read raw values
        raw_values = {
            "names": "",
            "grid_lines": [],
            "groups": [],
            "raw_outputs": "",
        }
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue
            
            if line.startswith("grid:"):
                i += 1
                while i < len(lines):
                    gline = lines[i].strip()
                    if ":" in gline and not gline.startswith("#"):
                         break
                    if gline and not gline.startswith("#"):
                        raw_values["grid_lines"].append(gline)
                    i += 1
                continue
                
            if line.startswith("groups:"):
                i += 1
                while i < len(lines):
                    gline = lines[i].strip()
                    if not gline or gline.startswith("#"):
                        i += 1
                        continue
                        
                    if ":" in gline and not (gline.startswith("-") or gline.startswith("'") or gline.startswith('"')):
                         if not gline.startswith("-"):
                             break
                    
                    raw_values["groups"].append(gline)
                    i += 1
                continue
                
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == "names":
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    raw_values["names"] = value
                elif key == "outputs":
                    raw_values["raw_outputs"] = value
            
            i += 1
            
        # Phase 2: Validate and Process
        if not raw_values["names"]:
             raise ValueError("Missing 'names' parameter")
             
        if raw_values["raw_outputs"]:
             raise ValueError("'outputs' parameter is deprecated. Please use 'grid' block instead.")
             
        if not raw_values["grid_lines"]:
             raise ValueError("Missing 'grid' block.")
             
        config["names"] = raw_values["names"]
        
        # Calculate Permutation for Axis Swap (Rows=FirstVars, Cols=Rest)
        # Schemdraw default: Top=First, Left=Rest. 
        # But we want Left=First, Top=Rest.
        # So we swap: schemdraw_names = Rest + First.
        
        num_vars = len(config["names"])
        split_idx = num_vars // 2
        
        row_vars = config["names"][:split_idx]
        col_vars = config["names"][split_idx:]
        
        # Schemdraw expects: Cols + Rows
        config["schemdraw_names"] = col_vars + row_vars
        
        # Permutation map: new_idx -> old_idx needed for cell permutation
        permute_indices = []
        # First part of new string comes from indices split_idx to end
        permute_indices.extend(range(split_idx, num_vars))
        # Second part comes from 0 to split_idx
        permute_indices.extend(range(0, split_idx))
        
        # Parse Grid
        config["truthtable"] = self._parse_grid_to_truthtable(num_vars, raw_values["grid_lines"])
        
        # Parse Groups with Permutation
        for gline in raw_values["groups"]:
            # Parse line (same logic as before)
            content = gline.lstrip("- ").strip()
            cells_str = content
            params = {}
            if ":" in content:
                parts = content.split(":", 1)
                cells_str = parts[0].strip()
                param_str = parts[1].strip()
                for p in param_str.split(","):
                     if "=" in p:
                         pk, pv = p.split("=", 1)
                         params[pk.strip()] = pv.strip()

                # Auto-styling: Enhanced Palette
                if "color" in params:
                    raw_color = params["color"].lower()
                    
                    # Define Palette (Border Color [Medium Pastel], Fill Color [Light Pastel])
                    palette = {
                        "red":     {"color": "#ff9999", "fill": "#ffcccc"},
                        "blue":    {"color": "#9999ff", "fill": "#ccccff"},
                        "green":   {"color": "#99ff99", "fill": "#ccffcc"},
                        "yellow":  {"color": "#e6e600", "fill": "#ffffcc"}, 
                        "orange":  {"color": "#ffcc99", "fill": "#ffebcc"},
                        "purple":  {"color": "#cc99ff", "fill": "#e6ccff"},
                        "cyan":    {"color": "#99ffff", "fill": "#ccffff"},
                        "magenta": {"color": "#ff99ff", "fill": "#ffccff"},
                        "teal":    {"color": "#99ffcc", "fill": "#ccffeb"},
                        "pink":    {"color": "#ff99cc", "fill": "#ffccdd"},
                        "lime":    {"color": "#99ff99", "fill": "#e6ffcc"},
                        "indigo":  {"color": "#9999ff", "fill": "#ccccff"},
                        "violet":  {"color": "#cc99ff", "fill": "#f2ccff"},
                        "gray":    {"color": "#b3b3b3", "fill": "#e0e0e0"},
                    }
                    
                    if raw_color in palette:
                        style = palette[raw_color]
                        # Apply border color
                        params["color"] = style["color"]
                        
                        # Apply fill if not specified
                        if "fill" not in params:
                            params["fill"] = style["fill"]
                            
                        # CRITICAL: 
                        # 1. zorder=2.5: Above Grid (z=2), Below Text (z=3).
                        # 2. lw=2: Thicker than grid (1.25) to mask it completely.
                        params["zorder"] = 2.5
                        params["lw"] = 2


            cells_str = cells_str.replace('"', '').replace("'", "")
            cells_list = cells_str.split()
            
            # PERMUTE CELL INDICES
            permuted_cells = []
            for cell in cells_list:
                if len(cell) != num_vars:
                    # Could warn/skip. Skipping invalid pattern.
                    continue
                # Permute
                new_cell = "".join([cell[i] for i in permute_indices])
                permuted_cells.append(new_cell)
            
            if permuted_cells:
                pattern = self._derive_pattern(permuted_cells)
                if pattern:
                    config["groups"][pattern] = params

        return config

    def _parse_grid_to_truthtable(self, num_vars: int, grid_lines: list[str]) -> list[tuple[str, str]]:
        """Parse grid and return truthtable with keys permuted for schemdraw (Col+Row)."""
        gray_2 = ['00', '01', '11', '10']
        gray_1 = ['0', '1']
        
        # Determines rows/cols based on standard split logic (same as _parse_config)
        split_idx = num_vars // 2
        num_rows_vars = split_idx
        num_cols_vars = num_vars - split_idx
        
        if num_rows_vars == 1:
            rows_gray = gray_1
        elif num_rows_vars == 2:
            rows_gray = gray_2
        else: 
             rows_gray = [] 

        if num_cols_vars == 1:
            cols_gray = gray_1
        elif num_cols_vars == 2:
            cols_gray = gray_2
        else:
             cols_gray = []

        if len(grid_lines) != len(rows_gray):
            raise ValueError(f"Grid must have {len(rows_gray)} rows for {num_vars} variables")
            
        grid_vals = []
        for l in grid_lines:
            vals = l.split()
            if len(vals) != len(cols_gray):
                raise ValueError(f"Grid must have {len(cols_gray)} columns per row")
            grid_vals.append(vals)
            
        tt = []
        for r_idx, r_val in enumerate(rows_gray):
            for c_idx, c_val in enumerate(cols_gray):
                val = grid_vals[r_idx][c_idx]
                # Key for schemdraw (Axis Swap): ColBits + RowBits
                key = c_val + r_val
                tt.append((key, val))
                
        return tt


    def _derive_pattern(self, cells: list[str]) -> str | None:
        """Derive Schemdraw wildcard pattern from list of cells."""
        if not cells:
            return None
            
        n = len(cells[0])
        # Verify all cells have same length
        if any(len(c) != n for c in cells):
            return None
            
        pattern = []
        for i in range(n):
            bits = set(c[i] for c in cells)
            if len(bits) == 1:
                pattern.append(bits.pop())
            else:
                pattern.append('.')
        
        return "".join(pattern)

    def _render_kmap(self, config: dict) -> bytes:
        try:
            schemdraw.use("svg")
        except Exception:
            pass
            
        d = Drawing()
        # Pass groups if present
        kwargs = {}
        if config["groups"]:
            kwargs["groups"] = config["groups"]
            
        d.add(logic.Kmap(names=config["schemdraw_names"], truthtable=config["truthtable"], **kwargs))
        
        svg_bytes = d.get_imagedata("svg")
        
        # Explicitly close all figures to prevent "More than 20 figures have been opened" warning
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except Exception:
            pass

        # Inject custom class to allow CSS exclusion
        try:
             svg_str = svg_bytes.decode("utf-8")
             if "<svg " in svg_str:
                 svg_str = svg_str.replace("<svg ", '<svg class="kmap-graph" ', 1)
                 return svg_str.encode("utf-8")
        except Exception:
             pass
             
        return svg_bytes
