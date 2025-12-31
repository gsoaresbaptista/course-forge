(function () {
    'use strict';

    async function inlineSVGs() {
        const images = document.querySelectorAll('img[src$=".svg"]');
        const promises = Array.from(images).map(async (img) => {
            try {
                const response = await fetch(img.src);
                if (!response.ok) return;
                const svgText = await response.text();

                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(svgText, "image/svg+xml");
                const svgElement = xmlDoc.querySelector('svg');

                if (!svgElement) return;

                const imgStyle = img.getAttribute('style');

                Array.from(img.attributes).forEach(attr => {
                    if (attr.name !== 'src' && attr.name !== 'alt') {
                        svgElement.setAttribute(attr.name, attr.value);
                    }
                });

                if (imgStyle) {
                    svgElement.setAttribute('style', imgStyle);
                }

                const widthAttr = img.getAttribute('width');
                const styleContainsWidth = imgStyle && imgStyle.includes('width');

                if (styleContainsWidth || (widthAttr && widthAttr.includes('%'))) {
                    // Ensure viewBox exists before removing width/height to preserve aspect ratio
                    if (!svgElement.getAttribute('viewBox')) {
                        const origWidth = svgElement.getAttribute('width');
                        const origHeight = svgElement.getAttribute('height');
                        if (origWidth && origHeight) {
                            const w = parseFloat(origWidth);
                            const h = parseFloat(origHeight);
                            if (!isNaN(w) && !isNaN(h) && w > 0 && h > 0) {
                                svgElement.setAttribute('viewBox', `0 0 ${w} ${h}`);
                            }
                        }
                    }
                    svgElement.removeAttribute('width');
                    svgElement.removeAttribute('height');
                }

                if (!svgElement.style.display) {
                    svgElement.style.display = 'block';
                }

                img.parentNode.replaceChild(svgElement, img);
            } catch (error) {
                console.error('Error inlining SVG:', error);
            }
        });
        await Promise.all(promises);
    }

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
                    seed: 42,
                    stroke: stroke !== 'none' ? stroke : undefined,
                    strokeWidth: strokeWidth,
                    fill: fill !== 'none' ? fill : undefined,
                    fillWeight: 3,
                };

                let sketch = null;

                try {
                    if (tag === 'path') {
                        const d = element.getAttribute('d');
                        if (!d) {
                            console.warn('Path element has no d attribute:', element);
                            return;
                        }
                        sketch = rc.path(d, options);
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
                        const x = parseFloat(element.getAttribute('x') || 0);
                        const y = parseFloat(element.getAttribute('y') || 0);
                        const w = parseFloat(element.getAttribute('width') || 0);
                        const h = parseFloat(element.getAttribute('height') || 0);
                        if (w === 0 || h === 0) {
                            console.warn('Rect has zero dimensions:', element);
                            return;
                        }
                        sketch = rc.rectangle(x, y, w, h, options);
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

                    if (!sketch) {
                        console.warn('No sketch created for:', tag, element);
                        return;
                    }

                    const transform = element.getAttribute('transform');
                    if (transform) sketch.setAttribute('transform', transform);

                    Array.from(element.attributes).forEach(a => {
                        if (!['d', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'width', 'height', 'points', 'style', 'class'].includes(a.name)) {
                            sketch.setAttribute(a.name, a.value);
                        }
                    });

                    sketch.classList.add('rough-sketch');

                    element.parentNode.insertBefore(sketch, element);
                    element.setAttribute('visibility', 'hidden');

                } catch (e) {
                    console.error('Error processing element:', tag, element, e);
                }
            });
        });
    }

    async function init() {
        await inlineSVGs();
        applySketchEffect();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
