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
    ARROW_SIZE = 5  # Smaller arrows
    
    # Colors (adjusted to orange/brown theme)
    PULSE_COLOR = "#92400e"  # Dark orange/brown (amber-800)
    AXIS_COLOR = "#92400e"   # Same as pulse for consistency
    TEXT_COLOR = "#431407"   # Very dark brown
    BASELINE_COLOR = "#d6d3d1"  # Warm gray

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            code = match.group("code").strip()
            attrs = self.parse_svg_attributes(match)
            
            # Check for explicitly declared "group" mode in attributes
            # We can override this logic inside _parse_waveform_config too
            is_group = "group" in match.group(0).split('\n')[0] 

            try:
                config = self._parse_waveform_config(code)
                
                # Determine render mode based on config structure
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
        """Parse the declarative waveform configuration.
        
        Supports two modes:
        1. Single waveform (legacy): define y-axis labels and pulses
        2. Group/Multi waveform: define multiple named channels
        """
        config = {
            "x_axis": "Time",
            # Single mode specific
            "y_axis_high": "High",
            "y_axis_low": "Low",
            "pulses": [],
            # Group mode specific
            "channels": [] # List of {"name": str, "pulses": list}
        }
        
        has_group_channels = False
        
        for line in code.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            if line.startswith("y-axis:"):
                # Single mode: Parse "y-axis: "High label" | "Low label""
                value = line[7:].strip()
                parts = value.split("|")
                if len(parts) >= 1:
                    config["y_axis_high"] = self._clean_label(parts[0])
                if len(parts) >= 2:
                    config["y_axis_low"] = self._clean_label(parts[1])
                    
            elif line.startswith("x-axis:"):
                value = line[7:].strip()
                config["x_axis"] = self._clean_label(value)
                
            elif line.startswith("pulses:"):
                # Single mode pulse definition
                value = line[7:].strip()
                config["pulses"] = self._parse_pulses(value)
                
            elif ":" in line:
                # Potential channel definition: "Name": pulses...
                key, value = line.split(":", 1)
                key = self._clean_label(key)
                
                # If key is NOT a reserved keyword, assume it's a channel name
                if key not in ["y-axis", "x-axis", "pulses", "width", "height", "centered"]:
                    has_group_channels = True
                    config["channels"].append({
                        "name": key,
                        "pulses": self._parse_pulses(value.strip())
                    })
        
        # If we detected channels but no single pulses, clean up standard config
        if has_group_channels:
            config["pulses"] = [] # Clear single mode pulses to force group render
            
        return config

    def _clean_label(self, text: str) -> str:
        """Remove surrounding quotes and clean up label text."""
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        # Handle escaped newlines
        text = text.replace("\\n", "\n")
        return text

    def _parse_pulses(self, pulse_str: str) -> list:
        """Parse pulse string into list of pulse definitions.
        
        Returns list of tuples: (type, width)
        where type is 'pulse' or 'gap'
        """
        pulses = []
        i = 0
        pulse_str = pulse_str.strip()
        
        while i < len(pulse_str):
            # Skip whitespace (normal gap)
            if pulse_str[i] == ' ':
                # Count consecutive spaces
                space_count = 0
                while i < len(pulse_str) and pulse_str[i] == ' ':
                    space_count += 1
                    i += 1
                # Only add gap if we have pulses already
                if pulses:
                    # If previous was pulse, add gap. If gap, extend it?
                    # Standard behavior: space = gap.
                    # If we just finished a pulse, add a gap.
                    # If we just finished a gap (from ...), extend it or add new?
                    # Let's keep specific logic: space always adds NORMAL_GAP * count
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
            
            # Unknown character, skip
            i += 1
        
        return pulses

    def _render_single_waveform(self, config: dict) -> bytes:
        """Generate SVG for a single waveform (legacy mode)."""
        pulses = config["pulses"]
        
        # Calculate total width needed for pulses
        pulse_width = sum(p[1] for p in pulses) if pulses else 0
        
        # SVG dimensions
        svg_width = self.AXIS_PADDING + pulse_width + self.RIGHT_PADDING
        svg_height = self.TOP_PADDING + self.PULSE_HEIGHT + self.BOTTOM_PADDING
        
        # Starting positions
        start_x = self.AXIS_PADDING
        baseline_y = self.TOP_PADDING + self.PULSE_HEIGHT
        high_y = self.TOP_PADDING
        
        svg_parts = []
        svg_parts.extend(self._generate_svg_header(svg_width, svg_height))
        
        # Draw single axis system
        svg_parts.extend(self._draw_axis_lines(start_x, baseline_y, high_y, svg_width))
        svg_parts.append(f'<line x1="{start_x}" y1="{baseline_y}" x2="{start_x + pulse_width}" y2="{baseline_y}" stroke="{self.BASELINE_COLOR}" stroke-width="1" stroke-dasharray="4,2"/>')
        
        # Draw waveform
        path_d = self._generate_waveform_path(pulses, start_x, baseline_y, high_y)
        svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
        
        # Labels
        svg_parts.append('<!-- Labels -->')
        # Y labels
        svg_parts.extend(self._generate_text(config["y_axis_high"], start_x - 10, high_y + 5, 9, "end"))
        svg_parts.extend(self._generate_text(config["y_axis_low"], start_x - 10, baseline_y + 5, 9, "end"))
        # X label
        svg_parts.extend(self._generate_text(config["x_axis"], svg_width - 15, baseline_y + 20, 10, "end"))
        
        svg_parts.append('</svg>')
        return ''.join(part for part in svg_parts if part).encode('utf-8')

    def _render_group_waveform(self, config: dict) -> bytes:
        """Render multiple stacked waveforms."""
        channels = config["channels"]
        num_channels = len(channels)
        
        # Calculate width (max of all channels)
        max_pulse_width = 0
        for ch in channels:
            w = sum(p[1] for p in ch["pulses"])
            if w > max_pulse_width:
                max_pulse_width = w
                
        # Dimensions
        svg_width = self.AXIS_PADDING + max_pulse_width + self.RIGHT_PADDING
        # Height: Top padding + (Pulse height * N) + (Gap * N-1) + Bottom padding
        svg_height = self.TOP_PADDING + (num_channels * self.PULSE_HEIGHT) + ((num_channels - 1) * self.CHANNEL_GAP) + self.BOTTOM_PADDING
        
        svg_parts = []
        svg_parts.extend(self._generate_svg_header(svg_width, svg_height))
        
        current_y_top = self.TOP_PADDING
        start_x = self.AXIS_PADDING
        
        # X-axis label at the very bottom
        bottom_y = svg_height - 20
        svg_parts.extend(self._generate_text(config["x_axis"], svg_width - 15, bottom_y, 10, "end"))

        # Draw axis line at bottom
        svg_parts.append(f'<line x1="{start_x}" y1="{bottom_y - 15}" x2="{svg_width - 10}" y2="{bottom_y - 15}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>')

        for i, channel in enumerate(channels):
            baseline_y = current_y_top + self.PULSE_HEIGHT
            high_y = current_y_top
            
            # Channel Label (Name)
            # Center vertically relative to the pulse height
            label_y = current_y_top + (self.PULSE_HEIGHT / 2) + 4
            svg_parts.extend(self._generate_text(channel["name"], start_x - 10, label_y, 11, "end"))
            
            # Baseline dotted line
            svg_parts.append(f'<line x1="{start_x}" y1="{baseline_y}" x2="{start_x + max_pulse_width}" y2="{baseline_y}" stroke="{self.BASELINE_COLOR}" stroke-width="1" stroke-dasharray="4,2"/>')
            
            # Vertical axis for this channel (optional, simplistic)
            # svg_parts.append(f'<line x1="{start_x}" y1="{baseline_y}" x2="{start_x}" y2="{high_y}" stroke="{self.BASELINE_COLOR}" stroke-width="1"/>')

            # Draw waveform
            path_d = self._generate_waveform_path(channel["pulses"], start_x, baseline_y, high_y)
            svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
            
            # Move to next slot
            current_y_top += self.PULSE_HEIGHT + self.CHANNEL_GAP
            
        svg_parts.append('</svg>')
        return ''.join(part for part in svg_parts if part).encode('utf-8')

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
