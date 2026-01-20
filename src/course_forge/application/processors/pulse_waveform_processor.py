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

            try:
                config = self._parse_waveform_config(code)
                svg_data = self._render_waveform(config)
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
            "y_axis_high": "High",
            "y_axis_low": "Low",
            "x_axis": "Time",
            "pulses": [],
        }
        
        for line in code.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("y-axis:"):
                # Parse "y-axis: "High label" | "Low label""
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
                value = line[7:].strip()
                config["pulses"] = self._parse_pulses(value)
        
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
                if pulses and pulses[-1][0] == 'pulse':
                    pulses.append(('gap', self.NORMAL_GAP * max(1, space_count)))
                continue
            
            # Check for extra gap (...)
            if pulse_str[i:i+3] == '...':
                if pulses and pulses[-1][0] == 'gap':
                    # Extend existing gap
                    pulses[-1] = ('gap', pulses[-1][1] + self.EXTRA_GAP)
                else:
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

    def _render_waveform(self, config: dict) -> bytes:
        """Generate SVG for the waveform."""
        pulses = config["pulses"]
        
        # Calculate total width needed for pulses
        pulse_width = sum(p[1] for p in pulses)
        
        # SVG dimensions
        svg_width = self.AXIS_PADDING + pulse_width + self.RIGHT_PADDING
        svg_height = self.TOP_PADDING + self.PULSE_HEIGHT + self.BOTTOM_PADDING
        
        # Starting positions
        start_x = self.AXIS_PADDING
        baseline_y = self.TOP_PADDING + self.PULSE_HEIGHT
        high_y = self.TOP_PADDING
        
        # Build SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">',
            '<defs>',
            # Arrowhead with explicit stroke to match border color request
            f'  <marker id="arrowhead" markerWidth="{self.ARROW_SIZE}" markerHeight="{self.ARROW_SIZE}" refX="{self.ARROW_SIZE-1}" refY="{self.ARROW_SIZE/2}" orient="auto">',
            f'    <polygon points="0 0, {self.ARROW_SIZE} {self.ARROW_SIZE/2}, 0 {self.ARROW_SIZE}" fill="{self.AXIS_COLOR}" stroke="none"/>',
            '  </marker>',
            '</defs>',
            '',
            '<!-- Axes -->',
            f'<line x1="{start_x}" y1="{baseline_y}" x2="{svg_width - 10}" y2="{baseline_y}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>',
            f'<line x1="{start_x}" y1="{baseline_y + 5}" x2="{start_x}" y2="{high_y - 15}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>',
            '',
            '<!-- Baseline (low level) -->',
            f'<line x1="{start_x}" y1="{baseline_y}" x2="{start_x + pulse_width}" y2="{baseline_y}" stroke="{self.BASELINE_COLOR}" stroke-width="1" stroke-dasharray="4,2"/>',
        ]
        
        # Draw pulses
        svg_parts.append('')
        svg_parts.append('<!-- Pulses -->')
        
        current_x = start_x
        path_d = f"M {current_x} {baseline_y}"
        
        for pulse_type, width in pulses:
            if pulse_type == 'gap':
                # Stay at baseline during gaps
                current_x += width
                path_d += f" L {current_x} {baseline_y}"
            else:
                # Draw pulse: up, across, down
                path_d += f" L {current_x} {high_y}"  # Up
                current_x += width
                path_d += f" L {current_x} {high_y}"  # Across at high
                path_d += f" L {current_x} {baseline_y}"  # Down
        
        svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
        
        # Add labels - adjusted vertical positions and sizes
        svg_parts.append('')
        svg_parts.append('<!-- Labels -->')
        
        # Y-axis high label (multiline support)
        high_lines = config["y_axis_high"].split("\n")
        high_label_y = high_y + 5
        for i, line in enumerate(high_lines):
            y_pos = high_label_y + (i * 14)
            svg_parts.append(f'<text x="{start_x - 10}" y="{y_pos}" text-anchor="end" font-family="system-ui, -apple-system, sans-serif" font-size="9" fill="{self.TEXT_COLOR}">{self._escape_xml(line)}</text>')
        
        # Y-axis low label (multiline support)
        low_lines = config["y_axis_low"].split("\n")
        low_label_y = baseline_y - (len(low_lines) - 1) * 7
        for i, line in enumerate(low_lines):
            y_pos = low_label_y + (i * 14)
            svg_parts.append(f'<text x="{start_x - 10}" y="{y_pos}" text-anchor="end" font-family="system-ui, -apple-system, sans-serif" font-size="9" fill="{self.TEXT_COLOR}">{self._escape_xml(line)}</text>')
        
        # X-axis label
        svg_parts.append(f'<text x="{svg_width - 15}" y="{baseline_y + 20}" text-anchor="end" font-family="system-ui, -apple-system, sans-serif" font-size="10" fill="{self.TEXT_COLOR}">{self._escape_xml(config["x_axis"])}</text>')
        
        svg_parts.append('</svg>')
        
        # Join with empty string to avoid newlines that might cause markdown parser
        # to insert <p> tags inside the SVG
        return ''.join(part for part in svg_parts if part).encode('utf-8')

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
