import re
from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase


class PulseWaveformProcessor(SVGProcessorBase):
    """Processor for declarative pulse/waveform diagrams.
    
    Syntax:
        ```pulse.waveform centered width=500
        y-axis: "High label" | "Low label"
        x-axis: "Time"
        pulses: --- . --- . ... --- .
        ```
    
    Where:
        - `---` = long pulse (dash/traço)
        - `.` = short pulse (dot/ponto)  
        - `...` = extra space between pulses
        - Regular spaces = normal spacing
    """

    pattern = SVGProcessorBase.create_pattern("pulse.waveform", r"(?P<code>.*?)")

    # Pulse dimensions
    PULSE_HEIGHT = 40
    SHORT_PULSE_WIDTH = 15
    LONG_PULSE_WIDTH = 40
    NORMAL_GAP = 10
    EXTRA_GAP = 35
    
    # Axis and padding
    AXIS_PADDING = 140  # Increased to fit longer labels
    RIGHT_PADDING = 30
    TOP_PADDING = 30
    BOTTOM_PADDING = 50
    CHANNEL_GAP = 30 # Gap between stacked waveforms
    ARROW_SIZE = 5  
    
    # Colors 
    PULSE_COLOR = "#92400e"  # Dark orange/brown
    AXIS_COLOR = "#92400e"   
    TEXT_COLOR = "#431407"   
    BASELINE_COLOR = "#d6d3d1" 
    GRID_COLOR = "#a8a29e"   # Darker warm gray for better visibility

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            code = match.group("code").strip()
            attrs = self.parse_svg_attributes(match)

            try:
                config = self._parse_waveform_config(code)
                
                if "channels" in config and config["channels"]:
                     svg_data = self._render_group_waveform(config)
                else:
                     svg_data = self._render_single_waveform(config)
                
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph pulse-waveform-img",
                )
                svg_html = f'<div class="no-break">{svg_html}</div>'
                content = content.replace(match.group(0), svg_html)
            except Exception as e:
                error_msg = f'<div class="error">Pulse waveform error: {str(e)}</div>'
                content = content.replace(match.group(0), error_msg)

        return content

    def _parse_waveform_config(self, code: str) -> dict:
        """Parse the declarative waveform configuration."""
        config = {
            "x_axis": "Time",
            "y_axis_high": "High",
            "y_axis_low": "Low",
            "pulses": [],
            "channels": [],
            "ticks": [], # List of tick labels
            "grid": False # Default no grid lines
        }
        
        has_group_channels = False
        
        for line in code.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            if line.startswith("y-axis:"):
                value = line[7:].strip()
                parts = value.split("|")
                if len(parts) >= 1:
                    config["y_axis_high"] = self._clean_label(parts[0])
                if len(parts) >= 2:
                    config["y_axis_low"] = self._clean_label(parts[1])
                    
            elif line.startswith("x-axis:"):
                value = line[7:].strip()
                config["x_axis"] = self._clean_label(value)

            elif line.startswith("ticks:"):
                value = line[6:].strip()
                config["ticks"] = value.split()
                
            elif line.startswith("grid:"):
                value = line[5:].strip().lower()
                config["grid"] = value == "true"
                
            elif line.startswith("pulses:"):
                value = line[7:].strip()
                config["pulses"] = self._parse_pulses(value)
                
            elif ":" in line:
                key, value = line.split(":", 1)
                key = self._clean_label(key)
                
                if key not in ["y-axis", "x-axis", "pulses", "width", "height", "centered", "ticks", "grid"]:
                    has_group_channels = True
                    config["channels"].append({
                        "name": key,
                        "pulses": self._parse_pulses(value.strip())
                    })
        
        if has_group_channels:
            config["pulses"] = [] 
            
        return config

    def _clean_label(self, text: str) -> str:
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        text = text.replace("\\n", "\n")
        return text

    def _parse_pulses(self, pulse_str: str) -> list:
        """Parse pulse string into list of pulse definitions."""
        pulses = []
        i = 0
        pulse_str = pulse_str.strip()
        
        while i < len(pulse_str):
            # Check for marker (|)
            if pulse_str[i] == '|':
                pulses.append(('marker', 0))
                i += 1
                continue

            # Skip whitespace (normal gap)
            if pulse_str[i] == ' ':
                space_count = 0
                while i < len(pulse_str) and pulse_str[i] == ' ':
                    space_count += 1
                    i += 1
                if pulses:
                    pulses.append(('gap', self.NORMAL_GAP * max(1, space_count)))
                continue
            
            # Check for extra gap (...)
            if pulse_str[i:i+3] == '...':
                pulses.append(('gap', self.EXTRA_GAP))
                i += 3
                continue
            
            # Check for long pulse (---)
            if pulse_str[i:i+3] == '---':
                pulses.append(('pulse', self.LONG_PULSE_WIDTH))
                i += 3
                continue
            
            # Check for short pulse (.)
            if pulse_str[i] == '.':
                pulses.append(('pulse', self.SHORT_PULSE_WIDTH))
                i += 1
                continue
            
            i += 1
        
        return pulses

    def _collect_markers(self, pulses) -> list:
        """Calculate X positions of all markers in a pulse sequence."""
        markers = []
        current_x = self.AXIS_PADDING
        for p_type, width in pulses:
            if p_type == 'marker':
                markers.append(current_x)
            else:
                current_x += width
        return markers

    def _render_single_waveform(self, config: dict) -> bytes:
        pulses = config["pulses"]
        pulse_width = sum(p[1] for p in pulses) if pulses else 0
        
        markers = self._collect_markers(pulses)

        svg_width = self.AXIS_PADDING + pulse_width + self.RIGHT_PADDING
        svg_height = self.TOP_PADDING + self.PULSE_HEIGHT + self.BOTTOM_PADDING
        
        start_x = self.AXIS_PADDING
        baseline_y = self.TOP_PADDING + self.PULSE_HEIGHT
        high_y = self.TOP_PADDING
        
        svg_parts = []
        svg_parts.extend(self._generate_svg_header(svg_width, svg_height))
        
        # Grid lines and Ticks
        svg_parts.extend(self._draw_grid_and_ticks(markers, config.get("ticks", []), self.TOP_PADDING, baseline_y + 15, show_grid=config.get("grid", False)))

        # Axis
        svg_parts.extend(self._draw_axis_lines(start_x, baseline_y, high_y, svg_width))
        svg_parts.append(f'<line x1="{start_x}" y1="{baseline_y}" x2="{start_x + pulse_width}" y2="{baseline_y}" stroke="{self.BASELINE_COLOR}" stroke-width="1" stroke-dasharray="4,2"/>')
        
        path_d = self._generate_waveform_path(pulses, start_x, baseline_y, high_y)
        svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
        
        # Labels
        svg_parts.append('<!-- Labels -->')
        svg_parts.extend(self._generate_text(config["y_axis_high"], start_x - 10, high_y + 5, 9, "end"))
        svg_parts.extend(self._generate_text(config["y_axis_low"], start_x - 10, baseline_y + 5, 9, "end"))
        svg_parts.extend(self._generate_text(config["x_axis"], svg_width - 15, baseline_y + 20, 10, "end"))
        
        svg_parts.append('</svg>')
        return ''.join(part for part in svg_parts if part).encode('utf-8')

    def _render_group_waveform(self, config: dict) -> bytes:
        channels = config["channels"]
        num_channels = len(channels)
        
        # Calculate width and collect ALL unique marker positions across all channels
        max_pulse_width = 0
        all_markers = set()
        
        for ch in channels:
            w = sum(p[1] for p in ch["pulses"])
            if w > max_pulse_width:
                max_pulse_width = w
            
            # Collect markers for this channel
            ch_markers = self._collect_markers(ch["pulses"])
            all_markers.update(ch_markers)
                
        sorted_markers = sorted(list(all_markers))

        svg_width = self.AXIS_PADDING + max_pulse_width + self.RIGHT_PADDING
        svg_height = self.TOP_PADDING + (num_channels * self.PULSE_HEIGHT) + ((num_channels - 1) * self.CHANNEL_GAP) + self.BOTTOM_PADDING
        
        svg_parts = []
        svg_parts.extend(self._generate_svg_header(svg_width, svg_height))
        
        current_y_top = self.TOP_PADDING
        start_x = self.AXIS_PADDING
        bottom_y = svg_height - 20
        
        # Draw Grid and Ticks (spanning full height)
        # Grid goes from top padding to bottom axis
        svg_parts.extend(self._draw_grid_and_ticks(sorted_markers, config.get("ticks", []), self.TOP_PADDING, bottom_y, grid_bottom_y=bottom_y - 15, show_grid=config.get("grid", False)))

        # Draw X-axis label and line
        svg_parts.extend(self._generate_text(config["x_axis"], svg_width - 15, bottom_y, 10, "end"))
        svg_parts.append(f'<line x1="{start_x}" y1="{bottom_y - 15}" x2="{svg_width - 10}" y2="{bottom_y - 15}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>')

        for i, channel in enumerate(channels):
            baseline_y = current_y_top + self.PULSE_HEIGHT
            high_y = current_y_top
            
            label_y = current_y_top + (self.PULSE_HEIGHT / 2) + 4
            svg_parts.extend(self._generate_text(channel["name"], start_x - 10, label_y, 11, "end"))
            
            svg_parts.append(f'<line x1="{start_x}" y1="{baseline_y}" x2="{start_x + max_pulse_width}" y2="{baseline_y}" stroke="{self.BASELINE_COLOR}" stroke-width="1" stroke-dasharray="4,2"/>')
            
            path_d = self._generate_waveform_path(channel["pulses"], start_x, baseline_y, high_y)
            svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
            
            current_y_top += self.PULSE_HEIGHT + self.CHANNEL_GAP
            
        svg_parts.append('</svg>')
        return ''.join(part for part in svg_parts if part).encode('utf-8')

    def _draw_grid_and_ticks(self, markers, tick_labels, top_y, label_y, grid_bottom_y=None, show_grid=False) -> list:
        parts = []
        if grid_bottom_y is None:
            grid_bottom_y = label_y - 15 # Default for single waveform
            
        axis_y = grid_bottom_y
            
        for i, x_pos in enumerate(markers):
            # Draw optional vertical grid line (full height)
            if show_grid:
                parts.append(f'<line x1="{x_pos}" y1="{top_y}" x2="{x_pos}" y2="{axis_y}" stroke="{self.GRID_COLOR}" stroke-width="1" stroke-dasharray="2,2"/>')
            
            # Draw small tick mark on X axis (always)
            parts.append(f'<line x1="{x_pos}" y1="{axis_y}" x2="{x_pos}" y2="{axis_y + 4}" stroke="{self.AXIS_COLOR}" stroke-width="1.5"/>')
            
            # Draw tick label if available
            if i < len(tick_labels):
                parts.append(f'<text x="{x_pos}" y="{label_y}" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-size="9" fill="{self.TEXT_COLOR}">{self._escape_xml(tick_labels[i])}</text>')
                
        return parts

    def _generate_svg_header(self, width: float, height: float) -> list:
        return [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
            '<defs>',
            f'  <marker id="arrowhead" markerWidth="{self.ARROW_SIZE}" markerHeight="{self.ARROW_SIZE}" refX="{self.ARROW_SIZE-1}" refY="{self.ARROW_SIZE/2}" orient="auto">',
            f'    <polygon points="0 0, {self.ARROW_SIZE} {self.ARROW_SIZE/2}, 0 {self.ARROW_SIZE}" fill="{self.AXIS_COLOR}" stroke="none"/>',
            '  </marker>',
            '</defs>',
            ''
        ]

    def _draw_axis_lines(self, start_x, baseline_y, high_y, svg_width) -> list:
        return [
             f'<line x1="{start_x}" y1="{baseline_y}" x2="{svg_width - 10}" y2="{baseline_y}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>',
             f'<line x1="{start_x}" y1="{baseline_y + 5}" x2="{start_x}" y2="{high_y - 15}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>',
        ]

    def _generate_text(self, text: str, x, y, size, align) -> list:
        parts = []
        lines = text.split("\n")
        # Simple multiline support: grow downwards
        for i, line in enumerate(lines):
            dy = i * (size * 1.4)
            parts.append(f'<text x="{x}" y="{y + dy}" text-anchor="{align}" font-family="system-ui, -apple-system, sans-serif" font-size="{size}" fill="{self.TEXT_COLOR}">{self._escape_xml(line)}</text>')
        return parts

    def _generate_waveform_path(self, pulses, start_x, baseline_y, high_y) -> str:
        current_x = start_x
        path_d = f"M {current_x} {baseline_y}"
        
        # Start at baseline? Or logic level 0?
        # Logic: 
        # 'gap' = Logic 0 (baseline) BUT if we come from a pulse, we drop down.
        # 'pulse' = Logic 1 (high).
        
        # State tracking needed for cleaner transitions?
        # Current implementation assumes:
        # Pulse transitions: Up -> High -> Down
        # Gap transitions: Stay Low
        
        # Problem: Contiguous pulses (High -> High) shouldn't drop down.
        # But our syntax `--- .` implies separate pulses visually separated?
        # User example: `--- . ---`
        # If user wants ONE long pulse, they use `------`.
        # If `--- ---`, should it drop? Probably yes, to show 2 bits.
        # Let's keep current logic for now: every pulse starts from baseline and returns to baseline (RZ style? No, it looks NRZ but with implicit RZ between items?)
        
        # WAIT. The previous implementation:
        # for pulse: Up, Across, Down.
        # for gap: Across (at baseline).
        # This forces Return-to-Zero (RZ) behavior between every pulse item if there's a gap?
        # No, `pulses` loop:
        # If `pulse`: Up L L Down.
        # If `gap`: L (stay at baseline).
        
        # So `--- ---` would be: Up, Across, Down, Up, Across, Down. (Glitch to 0).
        # To support contiguous high (1111), the parser should merge contiguous pulse chars
        # OR we change rendering to be state-based.
        
        # For this iteration, I'll stick to the logic that worked for the single waveform
        # as the user was happy with it. Visual refactoring can be a later request.
        
        for pulse_type, width in pulses:
            if pulse_type == 'marker':
                continue
                
            if pulse_type == 'gap':
                # Stay at baseline
                current_x += width
                path_d += f" L {current_x} {baseline_y}"
            else:
                # Pulse
                path_d += f" L {current_x} {high_y}"  # Up
                current_x += width
                path_d += f" L {current_x} {high_y}"  # Across
                path_d += f" L {current_x} {baseline_y}"  # Down
                
        return path_d

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
