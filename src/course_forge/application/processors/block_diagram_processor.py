from schemdraw import dsp

from course_forge.domain.entities import ContentNode

from .schemdraw_processor import SchemdrawProcessor
from .svg_processor_base import SVGProcessorBase


class BlockDiagramProcessor(SchemdrawProcessor):
    """Processor for block diagram (DSP) code blocks using schemdraw.dsp."""

    pattern = SVGProcessorBase.create_pattern("blockdiagram.plot", r"(?P<code>.*?)")

    def _render_schemdraw(self, code: str) -> bytes:
        """Execute block diagram code with DSP elements directly in scope."""
        import schemdraw
        from schemdraw import Drawing
        import schemdraw.elements as elm
        import schemdraw.logic as logic
        import schemdraw.dsp as dsp
        import schemdraw.flow as flow
        import matplotlib.pyplot as plt

        try:
            schemdraw.use("matplotlib")
        except Exception:
            pass

        schemdraw.config(color='#333')

        plt.rcParams['savefig.transparent'] = True
        plt.rcParams['svg.fonttype'] = 'none'

        # Base context (same as SchemdrawProcessor)
        context = {
            "schemdraw": schemdraw,
            "Drawing": Drawing,
            "elm": elm,
            "logic": logic,
            "dsp": dsp,
            "flow": flow,
        }

        # Expose DSP elements directly in the execution scope
        dsp_elements = [
            "Arrow", "Line", "Box", "Square", "Circle",
            "Sum", "SumSigma", "Amp", "VGA",
            "Filter", "Mixer", "Oscillator", "OscillatorBox",
            "Speaker", "Adc", "Dac", "Demod", "Dot",
            "Antenna", "Wire", "Ic", "IcPin",
            "Circulator", "Isolator",
        ]
        for name in dsp_elements:
            if hasattr(dsp, name):
                context[name] = getattr(dsp, name)

        exec(code, context)

        # Look for the Drawing object
        drawing = None
        if "d" in context and isinstance(context["d"], Drawing):
            drawing = context["d"]
        else:
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

        try:
            plt.close('all')
        except Exception:
            pass

        return self._add_viewbox_padding(svg_data)
