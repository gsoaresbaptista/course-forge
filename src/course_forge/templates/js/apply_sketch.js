(function () {
    'use strict';

    function applySketchEffect() {
        const svgs = document.querySelectorAll('svg[data-sketch="true"]');

        svgs.forEach(svg => {
            const rc = rough.svg(svg);
            const elements = svg.querySelectorAll('path, line, circle, rect, ellipse, polygon, polyline');

            elements.forEach(element => {
                const tag = element.tagName.toLowerCase();
                const cs = getComputedStyle(element);

                const stroke = element.getAttribute('stroke') || cs.stroke;
                const strokeWidth = parseFloat(element.getAttribute('stroke-width') || cs.strokeWidth || 1);
                const fill = element.getAttribute('fill') || cs.fill;

                const options = {
                    roughness: 1.2,
                    bowing: 1.2,
                    seed: 42
                };

                let sketch = null;

                try {
                    if (tag === 'path') {
                        sketch = rc.path(element.getAttribute('d'), options);
                    } else if (tag === 'line') {
                        sketch = rc.line(
                            parseFloat(element.getAttribute('x1') || 0),
                            parseFloat(element.getAttribute('y1') || 0),
                            parseFloat(element.getAttribute('x2') || 0),
                            parseFloat(element.getAttribute('y2') || 0),
                            options
                        );
                    } else if (tag === 'circle') {
                        sketch = rc.circle(
                            parseFloat(element.getAttribute('cx') || 0),
                            parseFloat(element.getAttribute('cy') || 0),
                            parseFloat(element.getAttribute('r') || 0) * 2,
                            options
                        );
                    } else if (tag === 'rect') {
                        sketch = rc.rectangle(
                            parseFloat(element.getAttribute('x') || 0),
                            parseFloat(element.getAttribute('y') || 0),
                            parseFloat(element.getAttribute('width') || 0),
                            parseFloat(element.getAttribute('height') || 0),
                            options
                        );
                    } else if (tag === 'ellipse') {
                        sketch = rc.ellipse(
                            parseFloat(element.getAttribute('cx') || 0),
                            parseFloat(element.getAttribute('cy') || 0),
                            parseFloat(element.getAttribute('rx') || 0) * 2,
                            parseFloat(element.getAttribute('ry') || 0) * 2,
                            options
                        );
                    } else if (tag === 'polygon' || tag === 'polyline') {
                        const pts = element.getAttribute('points');
                        if (pts) {
                            const nums = pts.trim().split(/[\s,]+/).map(Number);
                            const verts = [];
                            for (let i = 0; i < nums.length; i += 2) {
                                verts.push([nums[i], nums[i + 1]]);
                            }
                            sketch = tag === 'polygon'
                                ? rc.polygon(verts, options)
                                : rc.linearPath(verts, options);
                        }
                    }

                    if (!sketch) return;

                    const transform = element.getAttribute('transform');
                    if (transform) sketch.setAttribute('transform', transform);

                    Array.from(element.attributes).forEach(a => {
                        if (!['d', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'width', 'height', 'points', 'style', 'class'].includes(a.name)) {
                            sketch.setAttribute(a.name, a.value);
                        }
                    });

                    sketch.classList.add('rough-sketch');

                    const applyStyle = n => {
                        if (n.tagName && n.tagName.toLowerCase() === 'path') {
                            n.style.setProperty('stroke', options.stroke, 'important');
                            n.style.setProperty('stroke-width', options.strokeWidth + 'px', 'important');
                            n.style.setProperty('fill', options.fill, 'important');
                            n.style.setProperty('stroke-linecap', 'round', 'important');
                            n.style.setProperty('stroke-linejoin', 'round', 'important');
                        }
                        Array.from(n.children || []).forEach(applyStyle);
                    };
                    applyStyle(sketch);

                    element.parentNode.insertBefore(sketch, element);
                    element.setAttribute('visibility', 'hidden');

                } catch (e) {
                    console.warn(e);
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applySketchEffect);
    } else {
        applySketchEffect();
    }
})();
