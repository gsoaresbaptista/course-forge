import os
import subprocess as original_subprocess
import schemdraw
from schemdraw import Drawing
import schemdraw.elements as elm
import schemdraw.logic as logic
import schemdraw.dsp as dsp
import schemdraw.flow as flow
import matplotlib
import matplotlib.pyplot as plt
import webbrowser

# Force non-interactive backends
matplotlib.use('Agg')

# Silence matplotlib show
plt.show = lambda *args, **kwargs: None
from matplotlib.figure import Figure
Figure.show = lambda *args, **kwargs: None

# Silence webbrowser
webbrowser.open = lambda *args, **kwargs: True
webbrowser.open_new = lambda *args, **kwargs: True
webbrowser.open_new_tab = lambda *args, **kwargs: True

# Silence os.system for xdg-open calls
_original_os_system = os.system
def _silenced_os_system(cmd):
    if isinstance(cmd, str) and ('xdg-open' in cmd or 'open ' in cmd):
        return 0
    return _original_os_system(cmd)
os.system = _silenced_os_system

# Silence subprocess module to prevent xdg-open
import subprocess
_original_subprocess_run = subprocess.run
_original_subprocess_call = subprocess.call
_original_subprocess_Popen = subprocess.Popen

def _is_viewer_command(args):
    if isinstance(args, str):
        return 'xdg-open' in args or 'open ' in args
    if isinstance(args, (list, tuple)) and len(args) > 0:
        first_arg = str(args[0])
        return 'xdg-open' in first_arg or first_arg == 'open'
    return False

def _silenced_subprocess_run(*args, **kwargs):
    if args and _is_viewer_command(args[0]):
        # Return a fake CompletedProcess
        return subprocess.CompletedProcess(args[0] if args else [], 0)
    return _original_subprocess_run(*args, **kwargs)

def _silenced_subprocess_call(*args, **kwargs):
    if args and _is_viewer_command(args[0]):
        return 0
    return _original_subprocess_call(*args, **kwargs)

class _SilencedPopen:
    def __init__(self, args, *a, **kw):
        if _is_viewer_command(args):
            self._returncode = 0
            self._silenced = True
            self._real = None
        else:
            self._real = _original_subprocess_Popen(args, *a, **kw)
            self._silenced = False
    
    def __getattr__(self, name):
        if self._silenced:
            # For silenced commands, return sensible defaults
            if name == 'stdin':
                return None
            if name == 'stdout':
                return None
            if name == 'stderr':
                return None
            if name == 'returncode':
                return self._returncode
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self._real, name)
            
    def communicate(self, *args, **kwargs):
        if self._silenced:
            return (b'', b'')
        return self._real.communicate(*args, **kwargs)
    
    def wait(self, *args, **kwargs):
        if self._silenced:
            return 0
        return self._real.wait(*args, **kwargs)
    
    @property
    def returncode(self):
        if self._silenced:
            return self._returncode
        return self._real.returncode
    
    @returncode.setter
    def returncode(self, val):
        if self._silenced:
            self._returncode = val
        else:
            self._real.returncode = val

subprocess.run = _silenced_subprocess_run
subprocess.call = _silenced_subprocess_call
subprocess.Popen = _SilencedPopen

# Silence Drawing.show
Drawing.show = lambda *args, **kwargs: None

# Use SVG backend
try:
    schemdraw.use('matplotlib')
except Exception:
    pass

from course_forge.domain.entities import ContentNode

from .svg_processor_base import SVGProcessorBase


class SchemdrawProcessor(SVGProcessorBase):
    """Processor for schemdraw code blocks."""

    pattern = SVGProcessorBase.create_pattern("schemdraw.plot", r"(?P<code>.*?)")

    def execute(self, node: ContentNode, content: str) -> str:
        matches = list(self.pattern.finditer(content))

        for match in matches:
            code = match.group("code").strip()
            attrs = self.parse_svg_attributes(match)

            try:
                svg_data = self._render_schemdraw(code)
                svg_html = self.generate_inline_svg(
                    svg_data,
                    attrs["width"],
                    attrs["height"],
                    attrs["centered"],
                    attrs["sketch"],
                    css_class="svg-graph schemdraw-plot-img",
                )

                # Wrap in no-break div for print layout if needed, 
                # following DigitalCircuitProcessor pattern
                svg_html = f'<div class="no-break">{svg_html}</div>'

                content = content.replace(match.group(0), svg_html)
            except Exception as e:
                # In case of error, we can either leave the code block or show an error
                # For now, let's just log it or re-raise if we want to fail fast
                # A common pattern is to replace it with an error message
                error_msg = f'<div class="error">Schemdraw error: {str(e)}</div>'
                content = content.replace(match.group(0), error_msg)

        return content

    def _render_schemdraw(self, code: str) -> bytes:
        """Execute schemdraw code and return SVG bytes."""
        # Force SVG backend to avoid popup windows and Tkinter issues
        try:
            schemdraw.use("matplotlib")
        except Exception:
            # Fallback if use() is not available or fails
            pass

        # Set default color to #333
        schemdraw.config(color='#333')
        
        # Configure matplotlib for SVG output
        # Ensure transparent background and use text elements instead of paths
        plt.rcParams['savefig.transparent'] = True
        plt.rcParams['svg.fonttype'] = 'none'

        # Setup context with common schemdraw imports
        # We use the same dict for globals and locals to ensure 
        # names are accessible within functions defined in the code block.
        context = {
            "schemdraw": schemdraw,
            "Drawing": Drawing,
            "elm": elm,
            "logic": logic,
            "dsp": dsp,
            "flow": flow,
        }

        # Execute the code block
        exec(code, context)

        # Look for the Drawing object in the context
        drawing = None
        
        # Priority 1: Check if there's an object named 'd' (common convention)
        if "d" in context and isinstance(context["d"], Drawing):
            drawing = context["d"]
        else:
            # Priority 2: Find any Drawing object
            for val in context.values():
                if isinstance(val, Drawing):
                    drawing = val
                    break

        if drawing is None:
            raise ValueError(
                "No schemdraw.Drawing object found in code block. "
                "Ensure you use 'with Drawing() as d:' or create a Drawing object."
            )

        svg_data = drawing.get_imagedata("svg")
        
        # Explicitly close all figures to prevent "More than 20 figures have been opened" warning
        # and memory leaks.
        try:
            plt.close('all')
        except Exception:
            pass

        return self._add_viewbox_padding(svg_data)

    def _add_viewbox_padding(self, svg_bytes: bytes, padding: float = 10.0) -> bytes:
        """Add padding to SVG viewBox to prevent labels from being cut off.
        
        Args:
            svg_bytes: Raw SVG data as bytes
            padding: Padding to add to all sides (in SVG units)
            
        Returns:
            Modified SVG data with adjusted viewBox
        """
        import re
        
        svg_str = svg_bytes.decode('utf-8')
        
        # Find and parse the viewBox attribute
        viewbox_match = re.search(r'viewBox="([^"]+)"', svg_str)
        if viewbox_match:
            viewbox = viewbox_match.group(1)
            parts = viewbox.split()
            if len(parts) == 4:
                min_x, min_y, width, height = map(float, parts)
                # Add padding to all sides
                new_min_x = min_x - padding
                new_min_y = min_y - padding
                new_width = width + (padding * 2)
                new_height = height + (padding * 2)
                new_viewbox = f"{new_min_x} {new_min_y} {new_width} {new_height}"
                svg_str = svg_str.replace(f'viewBox="{viewbox}"', f'viewBox="{new_viewbox}"')
        
        # Strip all newlines to prevent Markdown parser from interpreting indented lines as code blocks
        svg_str = svg_str.replace('\n', '').replace('\r', '')
        
        return svg_str.encode('utf-8')
