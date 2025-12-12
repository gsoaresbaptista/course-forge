(function() {
    const FONT_FAMILY = "'Comic Neue', 'Comic Sans MS', cursive";

    const style = document.createElement('style');
    style.textContent = `
        .rough-svg { display: block; overflow: visible; max-width: 100%; height: auto; }
        .rough-svg text { font-family: ${FONT_FAMILY}; font-weight: bold; stroke: none !important; fill: currentColor; }
        .rough-svg .node rect, .rough-svg .node circle, .rough-svg .node polygon { stroke: currentColor; }
        g.ast-op path, g.ast-op rect, g.ast-op circle, g.ast-op polygon { color: #42A5F5; fill: #42A5F5; }
        g.ast-op text { fill: #000 !important; }
        g.ast-leaf path, g.ast-leaf rect, g.ast-leaf circle, g.ast-leaf polygon { color: #66BB6A; }
        g.ast-leaf text { fill: #1B5E20 !important; }
        g.edgePath path { color: #555555; }
        @media (prefers-color-scheme: dark) {
            g.ast-op path, g.ast-op rect { color: #000; fill: #555; }
            g.ast-op text { fill: #000 !important; }
            g.ast-leaf { color: #000; }
            g.edgePath path { color: #CCC; }
        }
    `;
    document.head.appendChild(style);

    const getVal = (el, attr) => parseFloat(el.getAttribute(attr) || 0);

    function roughify(original) {
        const svg = original.cloneNode(true);
        svg.classList.add('rough-svg');
        svg.removeAttribute('style');
        
        const rc = rough.svg(svg);
        const els = svg.querySelectorAll("path, circle, rect, ellipse, line, polygon, polyline");

        els.forEach(el => {
            if (el.closest('foreignObject') || el.closest('defs') || el.closest('marker')) return;
            
            const stroke = el.getAttribute('stroke');
            const fill = el.getAttribute('fill');
            if ((stroke === 'transparent' || stroke === 'none') && (!fill || fill === 'none')) {
                el.style.opacity = '0';
                return;
            }

            const wrapper = el.closest('.ast-op, .ast-leaf, .node, .edgePath') || el;
            const isSolid = wrapper.classList.contains('ast-op');
            
            const opts = {
                roughness: wrapper.classList.contains('edgePath') ? 0.8 : 1.5,
                bowing: 0.2, stroke: 'currentColor', strokeWidth: 1.5,
                fillStyle: isSolid ? 'solid' : 'hachure',
                fillWeight: 0.5,
                fill: (isSolid || (fill && fill !== 'none' && fill !== '#000')) ? 'currentColor' : undefined
            };

            let node = null;
            const tag = el.tagName.toLowerCase();

            try {
                if (tag === 'path') node = rc.path(el.getAttribute('d'), opts);
                else if (tag === 'circle') node = rc.circle(getVal(el, 'cx'), getVal(el, 'cy'), getVal(el, 'r') * 2, opts);
                else if (tag === 'rect') node = rc.rectangle(getVal(el, 'x'), getVal(el, 'y'), getVal(el, 'width'), getVal(el, 'height'), opts);
                else if (tag === 'ellipse') node = rc.ellipse(getVal(el, 'cx'), getVal(el, 'cy'), getVal(el, 'rx') * 2, getVal(el, 'ry') * 2, opts);
                else if (tag === 'line') node = rc.line(getVal(el, 'x1'), getVal(el, 'y1'), getVal(el, 'x2'), getVal(el, 'y2'), opts);
                else if (tag === 'polygon' || tag === 'polyline') {
                    const pts = (el.getAttribute('points') || '').trim().split(/\s+|,/).map(Number);
                    const pairs = [];
                    for(let i=0; i<pts.length; i+=2) if(!isNaN(pts[i])) pairs.push([pts[i], pts[i+1]]);
                    node = tag === 'polygon' ? rc.polygon(pairs, opts) : rc.linearPath(pairs, opts);
                }
            } catch (e) {}

            if (node) {
                if (el.getAttribute('class')) node.setAttribute('class', el.getAttribute('class'));
                node.style.stroke = 'currentColor';
                if (opts.fill) node.style.fill = 'currentColor';
                el.parentNode.insertBefore(node, el);
                el.remove();
            }
        });

        svg.querySelectorAll('text').forEach(t => {
            t.removeAttribute('style');
            t.removeAttribute('fill');
            t.removeAttribute('stroke');
        });

        return svg;
    }

    async function init() {
        if (!window.rough) return;

        const imgs = document.querySelectorAll('img[src$=".svg"]');
        for (const img of imgs) {
            try {
                const res = await fetch(img.src);
                if (!res.ok) continue;
                const doc = new DOMParser().parseFromString(await res.text(), "image/svg+xml").querySelector("svg");
                if (!doc) continue;
                
                if (img.width) doc.setAttribute("width", img.width);
                if (img.height) doc.setAttribute("height", img.height);
                if (img.className) img.classList.forEach(c => doc.classList.add(c));
                
                img.parentNode.replaceChild(roughify(doc), img);
            } catch (e) {}
        }

        const tick = () => {
            document.querySelectorAll('.mermaid svg:not(.rough-svg)').forEach(svg => {
                svg.parentNode.replaceChild(roughify(svg), svg);
            });
        };

        tick();
        setInterval(tick, 1500);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();