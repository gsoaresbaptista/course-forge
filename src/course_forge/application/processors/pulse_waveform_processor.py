import re
from course_forge.domain.entities import ContentNode
from .svg_processor_base import SVGProcessorBase


class PulseWaveformProcessor(SVGProcessorBase):
    """Processor for declarative pulse/waveform diagrams.
    
    Syntax:
        ```pulse.waveform centered width=500
        y-axis: "High" | "Low"
        x-axis: "Time"
        pulses: ---...----..
        ```
    
    Where:
        - `-` = high state (pulse)
        - `.` = low state (no pulse)
        - `|` = tick marker position (manual mode)
        
    Each character represents one unit of time.
    Example: `---...` = 3 units high, 3 units low
    """

    pattern = SVGProcessorBase.create_pattern("pulse.waveform", r"(?P<code>.*?)")

    # Dimensions
    PULSE_HEIGHT = 40
    UNIT_WIDTH = 10  # Width of each time unit (character)
    
    # Spacing
    CHANNEL_GAP = 30  # Gap between stacked waveforms
    ARROW_SIZE = 5
    
    # Colors 
    PULSE_COLOR = "#92400e"  # Dark orange/brown
    AXIS_COLOR = "#92400e"   
    TEXT_COLOR = "#431407"   
    BASELINE_COLOR = "#d6d3d1" 
    GRID_COLOR = "#a8a29e"   # Darker warm gray for better visibility
    ZEBRA_COLOR = "#f5f5f4"  # Very subtle gray for background stripes

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
            "y_axis_high": "",
            "y_axis_low": "",
            "pulses": [],
            "channels": [],
            "ticks": [], # List of tick labels
            "grid": False, # Default no grid lines
            "ticks_mode": "manual" # Mode for tick placement
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
                # X-axis is a single label, remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                config["x_axis"] = value

            elif line.startswith("ticks:"):
                value = line[6:].strip()
                if value.lower() == "auto":
                    config["ticks_mode"] = "auto"
                elif value.lower() == "manual":
                    config["ticks_mode"] = "manual"
                else:
                    # Treat as space-separated labels
                    config["ticks"] = value.split()
                    config["ticks_mode"] = "manual"
            
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

    def _estimate_text_height(self, text: str, font_size: float) -> float:
        """Estimate height of potentially multiline text."""
        if not text:
            return 0
        lines = text.split("\n")
        # Line height is approx 1.4 * font size
        return len(lines) * (font_size * 1.4)

    def _estimate_text_width(self, text: str, font_size: float) -> float:
        """Estimate the width of text in pixels.
        
        Using a safer factor of 0.7 to ensure we don't underestimate width
        for variable width fonts, preventing clipping.
        """
        if not text:
            return 0
        lines = text.split("\n")
        avg_char_width = font_size * 0.7 # Increased from 0.5 to 0.7 for safety
        return max(len(line) * avg_char_width for line in lines)
    
    def _calculate_left_padding(self, y_axis_high: str, y_axis_low: str) -> float:
        """Calculate left padding based on Y-axis labels."""
        gap = 10  # Gap between text and graph
        margin = 2 # Small safety margin
        
        if not y_axis_high and not y_axis_low:
            return 15
        
        # Calculate width of both Y-axis labels
        high_width = self._estimate_text_width(y_axis_high, 9) if y_axis_high else 0
        low_width = self._estimate_text_width(y_axis_low, 9) if y_axis_low else 0
        max_label_width = max(high_width, low_width)
        
        # We draw text at start_x - 10. So start_x must be at least:
        # width + 10 (gap) + margin
        return max_label_width + gap + margin
    
    def _clean_label(self, text: str) -> str:
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        text = text.replace("\\n", "\n")
        return text

    def _parse_pulses(self, pulse_string: str) -> list:
        """Parse pulse string into segments.
        
        Syntax: Each character represents one time unit:
        - `-` = high state
        - `.` = low state  
        - `|` = tick marker (zero width)
        
        Returns list of (type, width) tuples where:
        - type: 'high', 'low', or 'marker'
        - width: number of units * UNIT_WIDTH
        """
        pulses = []
        i = 0
        
        while i < len(pulse_string):
            char = pulse_string[i]
            
            if char == '|':
                # Marker for tick position
                pulses.append(('marker', 0))
                i += 1
            elif char == '-':
                # Count consecutive dashes (high state)
                count = 0
                while i < len(pulse_string) and pulse_string[i] == '-':
                    count += 1
                    i += 1
                pulses.append(('high', count * self.UNIT_WIDTH))
            elif char == '.':
                # Count consecutive dots (low state)
                count = 0
                while i < len(pulse_string) and pulse_string[i] == '.':
                    count += 1
                    i += 1
                pulses.append(('low', count * self.UNIT_WIDTH))
            else:
                # Skip any other characters (whitespace, etc)
                i += 1
        
        return pulses

    def _collect_markers(self, pulses, start_x: float, mode='manual') -> list:
        """Calculate X positions of markers.
        
        mode='manual': only where pulse_type == 'marker' (|)
        mode='auto': at every time unit (every character)
        """
        markers = []
        current_x = start_x
        
        # Always start with a marker at the beginning
        markers.append(current_x)
        
        for p_type, width in pulses:
            if p_type == 'marker':
                markers.append(current_x)
            else:
                if mode == 'auto':
                    # Add a marker for every unit
                    num_units = int(width / self.UNIT_WIDTH)
                    for _ in range(num_units):
                        current_x += self.UNIT_WIDTH
                        markers.append(current_x)
                else:
                    current_x += width
        
        # Sort and remove duplicates
        return sorted(list(set(markers)))

    def _render_single_waveform(self, config: dict) -> bytes:
        pulses = config["pulses"]
        pulse_width = sum(p[1] for p in pulses) if pulses else 0
        
        ticks_mode = config.get("ticks_mode", "manual")
        
        # Dynamic padding calculations
        y_high = config.get("y_axis_high", "")
        y_low = config.get("y_axis_low", "")
        x_axis_label = config.get("x_axis", "")
        
        left_padding = self._calculate_left_padding(y_high, y_low)
        start_x = left_padding
        
        # Now we can collect markers with the correct start_x
        markers = self._collect_markers(pulses, start_x, mode=ticks_mode)
        
        tick_labels = config.get("ticks", [])
        # Note: We do NOT auto-generate numeric labels for 'auto' mode anymore
        # as per user request to imply scale without clutter.


        top_padding = self.ARROW_SIZE + 2  # Minimized top margin
        
        # Check if high Y-axis label needs more top space
        if y_high:
            pass
            
        # Bottom padding: tick labels + margin + potential low y-axis label overflow
        tick_label_height = 10 if tick_labels else 0
        
        # Calculate how much space Y-axis low label needs below baseline
        # Refined calculation for tighter fit
        if y_low:
            num_lines = len(y_low.split('\n'))
            # last line starts at: 5 + (n-1)*line_height
            # we need space for that last line (approx font_size) + small descent (2px)
            line_height = 9 * 1.4
            last_line_offset = 5 + ((num_lines - 1) * line_height)
            # 9px font size, + 2px descent/margin
            y_low_depth = last_line_offset + 9 + 2
        else:
            y_low_depth = 0
            
        bottom_padding = max(tick_label_height + 5, y_low_depth) # Removed extra buffer
        
        # Right padding: arrow + gap + x label
        # Fully dynamic calculation:
        # We need space for: ARROW_SIZE + arrow_gap + label_width + safety_margin
        arrow_gap = 5
        x_label_width = self._estimate_text_width(x_axis_label, 10) if x_axis_label else 0
        right_padding = self.ARROW_SIZE + arrow_gap + x_label_width + 2 
        # Note: we use +2 instead of +15 because our width estimate (0.7) is now safer.
        # This complies with "rente" but safe.
        
        svg_width = left_padding + pulse_width + right_padding
        svg_height = top_padding + self.PULSE_HEIGHT + bottom_padding
        
        baseline_y = top_padding + self.PULSE_HEIGHT
        high_y = top_padding
        axis_line_y = baseline_y
        
        # Calculate positions
        x_axis_end = start_x + pulse_width + self.ARROW_SIZE
        x_label_start = x_axis_end + arrow_gap
        y_axis_top = high_y - self.ARROW_SIZE
        
        svg_parts = []
        svg_parts.extend(self._generate_svg_header(svg_width, svg_height))
        
        # Grid lines, Zebra and Ticks
        # specific tick label y position (baseline_y is axis line) -> moved down to +12
        # Explicitly pass grid_bottom_y=baseline_y to ensure ticks start at the axis
        svg_parts.extend(self._draw_grid_and_ticks(
            markers, tick_labels, top_padding, baseline_y + 12, 
            grid_bottom_y=baseline_y,
            show_grid=config.get("grid", False), zebra=config.get("grid", False),
            ticks_mode=ticks_mode
        ))

        # Axis lines
        svg_parts.append(f'<line x1="{start_x}" y1="{baseline_y + 5}" x2="{start_x}" y2="{y_axis_top}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>')
        svg_parts.append(f'<line x1="{start_x}" y1="{axis_line_y}" x2="{x_axis_end}" y2="{axis_line_y}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>')
        
        # Baseline line removed as requested
        
        # Waveform
        path_d = self._generate_waveform_path(pulses, start_x, baseline_y, high_y)
        svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
        
        # Labels
        svg_parts.append('<!-- Labels -->')
        if y_high:
            svg_parts.extend(self._generate_text(y_high, start_x - 10, high_y + 5, 9, "end"))
        if y_low:
            svg_parts.extend(self._generate_text(y_low, start_x - 10, baseline_y + 5, 9, "end"))
        if x_axis_label:
            svg_parts.extend(self._generate_text(x_axis_label, x_label_start, axis_line_y + 4, 10, "start"))
        
        svg_parts.append('</svg>')
        return ''.join(part for part in svg_parts if part).encode('utf-8')

    def _render_group_waveform(self, config: dict) -> bytes:
        channels = config["channels"]
        num_channels = len(channels)
        ticks_mode = config.get("ticks_mode", "manual")
        
        # Calculate max pulse width and longest channel name
        max_pulse_width = 0
        max_channel_name_width = 0
        
        for ch in channels:
            w = sum(p[1] for p in ch["pulses"])
            if w > max_pulse_width:
                max_pulse_width = w
            
            # Track longest channel name
            name_width = self._estimate_text_width(ch["name"], 11)
            if name_width > max_channel_name_width:
                max_channel_name_width = name_width
        
        tick_labels = config.get("ticks", [])
        # No auto numeric labels for group mode either

        # Dynamic padding calculations
        x_axis_label = config.get("x_axis", "")
        
        gap = 10
        margin = 2
        left_padding = max_channel_name_width + gap + margin
        # Ensure start_x covers text width + gap
        start_x = left_padding
        
        # Recalculate markers with correct start_x for all channels
        all_markers = set()
        for ch in channels:
            ch_markers = self._collect_markers(ch["pulses"], start_x, mode=ticks_mode)
            all_markers.update(ch_markers)
        sorted_markers = sorted(list(all_markers))
        top_padding = 5  # Minimized top margin
        
        # Bottom padding: x-axis line + tick labels + x label
        # Bottom padding: x-axis line + tick labels + x label + potential low y-axis label overflow in last channel?
        
        # Increased tick label height reserve
        tick_label_height = 10 if tick_labels else 0
        x_axis_space = 15  # Space for X-axis line and label
        # Tighter bottom padding
        bottom_padding = tick_label_height + x_axis_space # Removed extra buffer
        
        # Right padding: arrow + gap + x label
        arrow_gap = 5
        x_label_width = self._estimate_text_width(x_axis_label, 10) if x_axis_label else 0
        right_padding = self.ARROW_SIZE + arrow_gap + x_label_width + 2 # Dynamic safe margin
        
        svg_width = left_padding + max_pulse_width + right_padding
        svg_height = top_padding + (num_channels * self.PULSE_HEIGHT) + ((num_channels - 1) * self.CHANNEL_GAP) + bottom_padding
        
        svg_parts = []
        svg_parts.extend(self._generate_svg_header(svg_width, svg_height))
        
        current_y_top = top_padding
        start_x = left_padding
        axis_line_y = svg_height - bottom_padding + 5
        
        # Calculate positions
        x_axis_end = start_x + max_pulse_width + self.ARROW_SIZE
        x_label_start = x_axis_end + arrow_gap
        
        # Draw Grid and Ticks (spanning full height)
        # label_y passed as svg_height - bottom_padding + 12 (moved down from 20)
        # axis_line_y is at svg_height - bottom_padding + 5
        # So label is at axis_line + 12.
        svg_parts.extend(self._draw_grid_and_ticks(
            sorted_markers, tick_labels, top_padding, axis_line_y + 12, 
            grid_bottom_y=axis_line_y, show_grid=config.get("grid", False), zebra=config.get("grid", False),
            ticks_mode=ticks_mode
        ))

        # Draw X-axis line and label
        svg_parts.append(f'<line x1="{start_x}" y1="{axis_line_y}" x2="{x_axis_end}" y2="{axis_line_y}" stroke="{self.AXIS_COLOR}" stroke-width="1.5" marker-end="url(#arrowhead)"/>')
        if x_axis_label:
            svg_parts.extend(self._generate_text(x_axis_label, x_label_start, axis_line_y + 4, 10, "start"))

        for i, channel in enumerate(channels):
            baseline_y = current_y_top + self.PULSE_HEIGHT
            high_y = current_y_top
            
            label_y = current_y_top + (self.PULSE_HEIGHT / 2) + 4
            svg_parts.extend(self._generate_text(channel["name"], start_x - 10, label_y, 11, "end"))
            
            # Baseline line removed as requested
            
            path_d = self._generate_waveform_path(channel["pulses"], start_x, baseline_y, high_y)
            svg_parts.append(f'<path d="{path_d}" fill="none" stroke="{self.PULSE_COLOR}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
            
            current_y_top += self.PULSE_HEIGHT + self.CHANNEL_GAP
            
        svg_parts.append('</svg>')
        return ''.join(part for part in svg_parts if part).encode('utf-8')

    def _draw_grid_and_ticks(self, markers, tick_labels, top_y, label_y, grid_bottom_y=None, show_grid=False, zebra=False, ticks_mode="manual") -> list:
        parts = []
        if grid_bottom_y is None:
            grid_bottom_y = label_y - 15 # Default for single waveform
            
        axis_y = grid_bottom_y
        
        # Draw zebra stripes first (background)
        if zebra and len(markers) > 1:
            for i in range(len(markers) - 1):
                if i % 2 == 0:
                    x_start = markers[i]
                    x_end = markers[i+1]
                    width = x_end - x_start
                    if width > 0:
                        parts.append(f'<rect x="{x_start}" y="{top_y}" width="{width}" height="{axis_y - top_y}" fill="{self.ZEBRA_COLOR}" stroke="none"/>')
            
        for i, x_pos in enumerate(markers):
            # Draw optional vertical grid line (full height)
            # Only draw full grid line if manual mode (or explicit grid requested for manual)
            # User behavior: "Não suba as linhas verticias quando o tick for auto"
            if show_grid and ticks_mode == "manual":
                parts.append(f'<line x1="{x_pos}" y1="{top_y}" x2="{x_pos}" y2="{axis_y}" stroke="{self.GRID_COLOR}" stroke-width="1" stroke-dasharray="2,2"/>')
            elif show_grid and ticks_mode == "auto":
                 # In auto mode with grid=true, maybe we still want them? 
                 # User said: "Não suba as linhas verticias quando o tick for auto"
                 # So I will disable vertical lines for auto mode even if grid=True?
                 # Or implies grid=True is passed.
                 # Let's assume grid=True enables zebra/grid generally, but specific full vertical lines are suppressed for auto ticks.
                 # But let's check if there are major ticks?
                 # Simplest interpretation: If mode is auto, don't draw full vertical line from tick.
                 pass

            # Draw small tick mark on X axis (always)
            parts.append(f'<line x1="{x_pos}" y1="{axis_y}" x2="{x_pos}" y2="{axis_y + 4}" stroke="{self.AXIS_COLOR}" stroke-width="1.5"/>')
            
            # Draw tick label if available
            if i < len(tick_labels):
                label_text = tick_labels[i]
                # Skip label if it is '.' or empty
                if label_text and label_text.strip() != '.': 
                    parts.append(f'<text x="{x_pos}" y="{label_y}" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-size="9" fill="{self.TEXT_COLOR}">{self._escape_xml(label_text)}</text>')
                
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


    def _generate_text(self, text: str, x, y, size, align) -> list:
        parts = []
        lines = text.split("\n")
        # Simple multiline support: grow downwards
        for i, line in enumerate(lines):
            dy = i * (size * 1.4)
            parts.append(f'<text x="{x}" y="{y + dy}" text-anchor="{align}" font-family="system-ui, -apple-system, sans-serif" font-size="{size}" fill="{self.TEXT_COLOR}">{self._escape_xml(line)}</text>')
        return parts

    def _generate_waveform_path(self, pulses, start_x, baseline_y, high_y) -> str:
        """Generate SVG path for waveform.
        
        Creates smooth state transitions without unnecessary drops to baseline.
        """
        current_x = start_x
        current_y = baseline_y
        path_d = f"M {current_x} {current_y}"
        
        for pulse_type, width in pulses:
            if pulse_type == 'marker':
                continue
            
            target_y = high_y if pulse_type == 'high' else baseline_y
            
            # Transition to new state if different
            if target_y != current_y:
                path_d += f" L {current_x} {target_y}"
                current_y = target_y
            
            # Move across at current level
            current_x += width
            path_d += f" L {current_x} {current_y}"
        
        return path_d

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
