import re
from collections import defaultdict
from dataclasses import dataclass, field

import schemdraw
from schemdraw import Drawing
import schemdraw.dsp as dsp
import matplotlib
import matplotlib.pyplot as plt

from course_forge.domain.entities import ContentNode
from .schemdraw_processor import SchemdrawProcessor
from .svg_processor_base import SVGProcessorBase


# ---------------------------------------------------------------------------
# DSL data structures
# ---------------------------------------------------------------------------

@dataclass
class _Node:
    id: str
    type: str       # 'label', 'box', 'sum'
    text: str
    x: float = 0.0
    y: float = 0.0


@dataclass
class _Edge:
    source: str
    target: str
    arrow: bool = True
    sign: str = '+'
    path_idx: int = 0


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------

class BlockDiagramProcessor(SchemdrawProcessor):
    """Processor for block diagram code blocks (Python and DSL modes)."""

    pattern = SVGProcessorBase.create_pattern("blockdiagram.plot", r"(?P<code>.*?)")

    # Layout constants
    UNIT_X = 3.0
    UNIT_Y = 1.6
    BOX_W = 1.6
    BOX_H = 1.1

    # ------------------------------------------------------------------
    # Override: detect mode and dispatch
    # ------------------------------------------------------------------

    def _render_schemdraw(self, code: str) -> bytes:
        if self._is_dsl(code):
            return self._render_dsl(code)
        return self._render_python(code)

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_dsl(code: str) -> bool:
        python_kw = ('import ', 'from ', 'with ', 'Drawing', 'schemdraw', 'def ', 'class ')
        lines = [l.strip() for l in code.strip().splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        if not lines:
            return False
        for line in lines:
            if any(line.startswith(k) or k in line for k in python_kw):
                return False
        return all('->' in l or '--' in l for l in lines)

    # ------------------------------------------------------------------
    # Python mode (existing behaviour with DSP context)
    # ------------------------------------------------------------------

    def _render_python(self, code: str) -> bytes:
        import schemdraw
        from schemdraw import Drawing
        import schemdraw.elements as elm
        import schemdraw.logic as logic
        import schemdraw.dsp as dsp_mod
        import schemdraw.flow as flow

        try:
            schemdraw.use("matplotlib")
        except Exception:
            pass

        schemdraw.config(color='#333')
        plt.rcParams['savefig.transparent'] = True
        plt.rcParams['svg.fonttype'] = 'none'

        context = {
            "schemdraw": schemdraw, "Drawing": Drawing,
            "elm": elm, "logic": logic, "dsp": dsp_mod, "flow": flow,
        }
        for name in (
            "Arrow", "Line", "Box", "Square", "Circle",
            "Sum", "SumSigma", "Amp", "VGA",
            "Filter", "Mixer", "Oscillator", "OscillatorBox",
            "Speaker", "Adc", "Dac", "Demod", "Dot",
            "Antenna", "Wire", "Ic", "IcPin",
            "Circulator", "Isolator",
        ):
            if hasattr(dsp_mod, name):
                context[name] = getattr(dsp_mod, name)

        exec(code, context)

        drawing = None
        if "d" in context and isinstance(context["d"], Drawing):
            drawing = context["d"]
        else:
            for val in context.values():
                if isinstance(val, Drawing):
                    drawing = val
                    break
        if drawing is None:
            raise ValueError("No schemdraw.Drawing object found.")

        svg_data = drawing.get_imagedata("svg")
        try:
            plt.close('all')
        except Exception:
            pass
        return self._add_viewbox_padding(svg_data)

    # ------------------------------------------------------------------
    # DSL mode – Parse → Layout → Render
    # ------------------------------------------------------------------

    def _render_dsl(self, code: str) -> bytes:
        nodes, edges, paths = self._parse_dsl(code)
        self._layout(nodes, paths)
        return self._draw(nodes, edges, paths)

    # -- Parse ---------------------------------------------------------

    def _parse_dsl(self, code: str):
        nodes: dict[str, _Node] = {}
        edges: list[_Edge] = []
        paths: list[list[str]] = []

        for line in code.strip().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = re.split(r'\s*(->|--)\s*', line)
            path: list[str] = []
            connectors: list[str] = []

            for part in parts:
                part = part.strip()
                if part in ('->', '--'):
                    connectors.append(part)
                    continue
                if not part:
                    continue

                nid, ntype, text, sign = self._parse_token(part)
                if nid not in nodes:
                    nodes[nid] = _Node(id=nid, type=ntype, text=text)
                path.append(nid)

                if len(path) > 1:
                    conn = connectors[-1] if connectors else '->'
                    edges.append(_Edge(
                        source=path[-2], target=nid,
                        arrow=(conn == '->'), sign=sign,
                        path_idx=len(paths),
                    ))

            if path:
                paths.append(path)

        return nodes, edges, paths

    @staticmethod
    def _parse_token(token: str):
        """Returns (id, type, display_text, sign)."""
        m = re.match(r'^\[(.+)\]$', token)
        if m:
            t = m.group(1)
            return t, 'box', t, '+'

        m = re.match(r'^\(([+-])(.+)\)$', token)
        if m:
            sign, name = m.group(1), m.group(2).strip()
            return name, 'sum', name, sign

        return token, 'label', token, '+'

    # -- Layout --------------------------------------------------------

    def _layout(self, nodes: dict[str, _Node], paths: list[list[str]]):
        if not paths:
            return

        # Which paths each node appears in
        membership: dict[str, set[int]] = defaultdict(set)
        for i, path in enumerate(paths):
            for nid in path:
                membership[nid].add(i)
        shared = {n for n, s in membership.items() if len(s) > 1}

        if len(paths) == 1 or not shared:
            # Simple series
            for i, nid in enumerate(paths[0]):
                nodes[nid].x = float(i)
            return

        # --- Multi-path layout ---
        # 1) Assign x along path[0] (reference path)
        for i, nid in enumerate(paths[0]):
            nodes[nid].x = float(i)

        # 2) Build spine order (shared nodes by x)
        spine = sorted(shared, key=lambda n: nodes[n].x)

        # 3) For each secondary path, find segments between shared nodes
        #    and assign unique-node positions
        for pi in range(1, len(paths)):
            path = paths[pi]
            shared_in_path = [n for n in path if n in shared]
            if not shared_in_path:
                # No shared nodes – just lay out sequentially
                start_x = max(n.x for n in nodes.values()) + 2
                for j, nid in enumerate(path):
                    if nodes[nid].x == 0.0 and nid not in shared:
                        nodes[nid].x = start_x + j
                continue

            # Process segments between consecutive shared nodes in this path
            for seg_i in range(len(shared_in_path) - 1):
                s_start = shared_in_path[seg_i]
                s_end = shared_in_path[seg_i + 1]
                x0 = nodes[s_start].x
                x1 = nodes[s_end].x

                # Collect unique nodes in this segment
                i0 = path.index(s_start)
                i1 = path.index(s_end)
                unique = [n for n in path[i0 + 1:i1] if n not in shared]

                if not unique:
                    continue

                is_backward = x1 < x0  # feedback path

                if is_backward:
                    # Backward: distribute between x1 and x0 (no widening)
                    span = x0 - x1
                    step = span / (len(unique) + 1)
                    for j, nid in enumerate(unique):
                        nodes[nid].x = x0 - step * (j + 1)
                else:
                    # Forward: widen gap if needed
                    needed_width = len(unique) + 1
                    current_width = x1 - x0
                    if needed_width > current_width:
                        delta = needed_width - current_width
                        for n in nodes.values():
                            if n.x >= x1 and n.id != s_start:
                                n.x += delta
                        x1 = nodes[s_end].x

                    span = x1 - x0
                    step = span / (len(unique) + 1)
                    for j, nid in enumerate(unique):
                        nodes[nid].x = x0 + step * (j + 1)

            # Handle prefix (before first shared) and suffix (after last shared)
            first_shared_idx = path.index(shared_in_path[0])
            prefix = [n for n in path[:first_shared_idx] if n not in shared]
            for j, nid in enumerate(reversed(prefix)):
                nodes[nid].x = nodes[shared_in_path[0]].x - (j + 1)

            last_shared_idx = path.index(shared_in_path[-1])
            suffix = [n for n in path[last_shared_idx + 1:] if n not in shared]
            for j, nid in enumerate(suffix):
                nodes[nid].x = nodes[shared_in_path[-1]].x + (j + 1)

        # 4) Assign y positions
        # Shared nodes stay at y=0
        # For each segment group, find which paths contribute and offset them
        for pi, path in enumerate(paths):
            if pi == 0:
                # Count total parallel path groups to decide offsets
                pass

        # Collect all segments grouped by (start_shared, end_shared)
        segments: dict[tuple[str, str], list[int]] = defaultdict(list)
        for pi, path in enumerate(paths):
            shared_in_path = [n for n in path if n in shared]
            for seg_i in range(len(shared_in_path) - 1):
                key = (shared_in_path[seg_i], shared_in_path[seg_i + 1])
                segments[key].append(pi)

        # For each segment group, assign y offsets
        for (s_start, s_end), path_indices in segments.items():
            n_paths = len(path_indices)
            if n_paths == 1:
                # Single path – check if forward or backward
                pi = path_indices[0]
                path = paths[pi]
                x_start = nodes[s_start].x
                x_end = nodes[s_end].x
                is_feedback = x_end < x_start
                if pi == 0 and not is_feedback:
                    offset = 0.0  # main forward path stays on spine
                else:
                    offset = -1.0 if is_feedback else 1.0
                # Set y for unique nodes
                i0 = path.index(s_start)
                i1 = path.index(s_end)
                for nid in path[i0 + 1:i1]:
                    if nid not in shared:
                        nodes[nid].y = offset
            else:
                # Multiple parallel paths
                offsets = self._distribute_offsets(n_paths)
                for rank, pi in enumerate(path_indices):
                    path = paths[pi]
                    i0 = path.index(s_start)
                    i1 = path.index(s_end)
                    for nid in path[i0 + 1:i1]:
                        if nid not in shared:
                            nodes[nid].y = offsets[rank]

        # Handle nodes not in any segment (prefix/suffix of secondary paths)
        for pi in range(1, len(paths)):
            path = paths[pi]
            shared_in_path = [n for n in path if n in shared]
            if not shared_in_path:
                continue
            first_shared_idx = path.index(shared_in_path[0])
            for nid in path[:first_shared_idx]:
                if nid not in shared and nodes[nid].y == 0.0:
                    nodes[nid].y = -1.0 * pi
            last_shared_idx = path.index(shared_in_path[-1])
            for nid in path[last_shared_idx + 1:]:
                if nid not in shared and nodes[nid].y == 0.0:
                    nodes[nid].y = -1.0 * pi

    @staticmethod
    def _distribute_offsets(n: int) -> list[float]:
        if n == 1:
            return [1.0]
        if n == 2:
            return [1.0, -1.0]
        offsets = []
        for i in range(n):
            offsets.append(1.0 - (2.0 * i / (n - 1)))
        return offsets

    # -- Render --------------------------------------------------------

    def _draw(self, nodes: dict[str, _Node], edges: list[_Edge],
              paths: list[list[str]]) -> bytes:
        import schemdraw
        import schemdraw.dsp as dsp_mod

        try:
            schemdraw.use("matplotlib")
        except Exception:
            pass
        schemdraw.config(color='#333')
        plt.rcParams['savefig.transparent'] = True
        plt.rcParams['svg.fonttype'] = 'none'

        ux = self.UNIT_X
        uy = self.UNIT_Y

        # Count path membership for labels
        label_paths: dict[str, int] = {}
        for nid, node in nodes.items():
            if node.type == 'label':
                label_paths[nid] = sum(1 for p in paths if nid in p)

        with Drawing() as d:
            d.config(fontsize=14)
            elems: dict[str, object] = {}

            # Pass 1: Place all graphical nodes
            for nid, node in nodes.items():
                px = node.x * ux
                py = node.y * uy  # positive y = up in schemdraw
                if node.type == 'box':
                    elems[nid] = dsp_mod.Box(w=self.BOX_W, h=self.BOX_H).at(
                        (px, py)).anchor('center').label(self._fmt(node.text))
                elif node.type == 'sum':
                    elems[nid] = dsp_mod.SumSigma().at(
                        (px, py)).anchor('center')
                elif node.type == 'label':
                    if label_paths.get(nid, 1) > 1:
                        elems[nid] = dsp_mod.Dot().at((px, py))
                    else:
                        elems[nid] = None

            # Pass 2: Draw arrows for shared labels
            drawn_labels: set[str] = set()
            for nid, node in nodes.items():
                if node.type != 'label' or label_paths.get(nid, 1) <= 1:
                    continue
                if nid in drawn_labels:
                    continue
                px = node.x * ux
                py = node.y * uy
                is_end = any(p[-1] == nid for p in paths)
                
                # Check if we should use an arrow based on edges
                use_arrow = True
                for edge in edges:
                    if (edge.source == nid or edge.target == nid) and not edge.arrow:
                        use_arrow = False
                        break

                draw_fn = dsp_mod.Arrow if use_arrow else dsp_mod.Line
                
                if is_end:
                    # Output arrow after dot
                    draw_fn().at(elems[nid].center).right(
                        ux * 0.4).label(self._fmt(node.text), 'right')
                else:
                    # Input arrow before dot
                    draw_fn().at((px - ux * 0.4, py)).right(
                        ux * 0.4).label(self._fmt(node.text), 'left')
                drawn_labels.add(nid)

            # Pass 3: Draw connections per path
            drawn_outputs: set[str] = set()
            for pi, path in enumerate(paths):
                for i in range(len(path) - 1):
                    src_id, tgt_id = path[i], path[i + 1]
                    src, tgt = nodes[src_id], nodes[tgt_id]

                    edge = next(
                        (e for e in edges
                         if e.source == src_id and e.target == tgt_id
                         and e.path_idx == pi), None)
                    if edge is None:
                        continue

                    src_elem = elems.get(src_id)
                    tgt_elem = elems.get(tgt_id)

                    # Handle non-shared input label: draw arrow directly
                    # to next element to avoid gap
                    if i == 0 and src.type == 'label' and src_elem is None:
                        tgt_in = self._in_pt(src, tgt, tgt_elem, ux, uy)
                        arr_len = ux * 0.5
                        input_draw_fn = dsp_mod.Arrow if edge.arrow else dsp_mod.Line
                        input_draw_fn().at(
                            (tgt_in[0] - arr_len, tgt_in[1])).right(
                            arr_len).label(
                            self._fmt(src.text), 'left')
                        continue  # edge is rendered as part of input arrow

                    # Handle non-shared output label (last edge)
                    if (i == len(path) - 2 and tgt.type == 'label'
                            and tgt_id not in drawn_outputs
                            and label_paths.get(tgt_id, 1) <= 1):
                        src_out = self._out_pt(src, src_elem, ux, uy)
                        dsp_mod.Arrow().at(src_out).right(
                            ux * 0.4).label(self._fmt(tgt.text), 'right')
                        drawn_outputs.add(tgt_id)
                        continue

                    # Get source output point
                    src_out = self._out_pt(src, src_elem, ux, uy, tgt)

                    # Get target input point (anchor depends on direction)
                    tgt_in = self._in_pt(src, tgt, tgt_elem, ux, uy)

                    # Route the connection
                    self._route(dsp_mod, src, tgt, src_out, tgt_in,
                                edge, ux, uy)

        svg_data = d.get_imagedata("svg")
        try:
            plt.close('all')
        except Exception:
            pass
        return self._add_viewbox_padding(svg_data)

    @staticmethod
    def _out_pt(node, elem, ux, uy, tgt=None):
        """Get output point for a node."""
        if elem is None:
            return (node.x * ux, node.y * uy)
        if node.type == 'label':
            if hasattr(elem, 'center'):
                return elem.center
            if hasattr(elem, 'end'):
                return elem.end
        # Direction-aware: use W when target is to the left
        if tgt is not None and tgt.x < node.x:
            if hasattr(elem, 'W'):
                return elem.W
        if hasattr(elem, 'E'):
            return elem.E
        return (node.x * ux, node.y * uy)

    @staticmethod
    def _in_pt(src, tgt, tgt_elem, ux, uy):
        """Get input point for a target node based on source direction."""
        if tgt_elem is None:
            return (tgt.x * ux, tgt.y * uy)

        # Sum junction: choose anchor based on incoming direction
        if tgt.type == 'sum':
            if abs(src.y - tgt.y) < 0.01:
                return tgt_elem.W  # same level → west
            elif src.y > tgt.y:
                return tgt_elem.N  # coming from above → north
            else:
                return tgt_elem.S  # coming from below → south

        # Box or other: choose side based on direction
        if src.x <= tgt.x:
            if hasattr(tgt_elem, 'W'):
                return tgt_elem.W
        else:
            if hasattr(tgt_elem, 'E'):
                return tgt_elem.E
        return (tgt.x * ux, tgt.y * uy)

    @staticmethod
    def _route(dsp_mod, src, tgt, src_out, tgt_in, edge, ux, uy):
        """Route a connection between src_out and tgt_in."""
        sx, sy = src_out
        tx, ty = tgt_in
        draw_fn = dsp_mod.Arrow if edge.arrow else dsp_mod.Line

        if abs(sy - ty) < 0.01:
            # Same level → direct horizontal
            dx = tx - sx
            if abs(dx) > 0.01:
                draw_fn().at(src_out).right(dx) if dx > 0 else draw_fn().at(src_out).left(-dx)

        elif abs(src.y) < 0.01:
            # Fork: spine → branch (vertical first, then horizontal)
            dy = ty - sy
            if dy > 0:
                dsp_mod.Line().at(src_out).up(dy)
            else:
                dsp_mod.Line().at(src_out).down(-dy)
            # Now at (sx, ty) – go right to target
            dx = tx - sx
            if abs(dx) > 0.01:
                draw_fn().right(dx) if dx > 0 else draw_fn().left(-dx)

        elif abs(tgt.y) < 0.01:
            # Merge: branch → spine (horizontal to target x, then vertical)
            dx = tx - sx
            if abs(dx) > 0.01:
                dsp_mod.Line().at(src_out).right(dx) if dx > 0 else dsp_mod.Line().at(src_out).left(-dx)
            # Now at (tx, sy) – go vertical to target
            dy = ty - sy
            conn = draw_fn()
            if dy > 0:
                conn.up(dy)
            else:
                conn.down(-dy)
            if tgt.type == 'sum' and edge.sign == '-':
                conn.label('$-$', 'left')

        else:
            # Both off-spine → horizontal then vertical
            dx = tx - sx
            dy = ty - sy
            if abs(dx) > 0.01:
                dsp_mod.Line().at(src_out).right(dx) if dx > 0 else dsp_mod.Line().at(src_out).left(-dx)
            if abs(dy) > 0.01:
                draw_fn().up(dy) if dy > 0 else draw_fn().down(-dy)

    @staticmethod
    def _fmt(text: str) -> str:
        """Wrap text in LaTeX if it contains underscores or math."""
        if '$' in text:
            return text
        if '_' in text or '^' in text or '\\' in text:
            return f'${text}$'
        return text

