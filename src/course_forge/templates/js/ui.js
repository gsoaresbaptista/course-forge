/**
 * ui.js - General UI utilities for Course Forge.
 */

window.CourseForgeUI = (function () {
    return {
        /**
         * Initialize Lucide icons.
         */
        initIcons: function () {
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        },

        /**
         * Initialize copy buttons for code blocks with fallback for insecure contexts.
         */
        initCopyButtons: function () {
            const preBlocks = document.querySelectorAll('pre[class*="language-"]');
            preBlocks.forEach(pre => {
                // Avoid duplicate buttons
                if (pre.querySelector('.copy-button')) return;

                const button = document.createElement('button');
                button.className = 'copy-button';
                button.setAttribute('aria-label', 'Copiar código');
                button.innerHTML = '<i data-lucide="copy"></i>';

                pre.appendChild(button);

                button.addEventListener('click', async () => {
                    const code = pre.querySelector('code');
                    if (!code) return;

                    const text = code.innerText;
                    let success = false;

                    try {
                        // Try modern API first (requires Secure Context)
                        if (navigator.clipboard && window.isSecureContext) {
                            await navigator.clipboard.writeText(text);
                            success = true;
                        } else {
                            // Fallback for insecure contexts (http://0.0.0.0) or older browsers
                            const textArea = document.createElement('textarea');
                            textArea.value = text;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-9999px';
                            textArea.style.top = '0';
                            document.body.appendChild(textArea);
                            textArea.focus();
                            textArea.select();

                            try {
                                success = document.execCommand('copy');
                            } catch (err) {
                                console.error('Fallback copy failed', err);
                            }

                            document.body.removeChild(textArea);
                        }

                        if (success) {
                            // Visual feedback
                            button.innerHTML = '<i data-lucide="check" style="color: #1dac52ff;"></i>';
                            this.initIcons();

                            setTimeout(() => {
                                button.innerHTML = '<i data-lucide="copy"></i>';
                                this.initIcons();
                            }, 2000);
                        }
                    } catch (err) {
                        console.error('Failed to copy: ', err);
                    }
                });
            });

            // Initial Lucide pass for injected buttons
            this.initIcons();
        },
        /**
         * Initialize collapsible example blocks.
         * Wraps content after .example-title in a .example-content div,
         * adds a chevron icon. Persists state via localStorage.
         */
        initExamples: function () {
            var pageKey = location.pathname;
            var examples = document.querySelectorAll('.example');
            examples.forEach(function (example, idx) {
                var title = example.querySelector('.example-title');
                if (!title || title.dataset.initialized) return;
                title.dataset.initialized = 'true';

                // Add chevron icon to title
                var chevron = document.createElement('i');
                chevron.setAttribute('data-lucide', 'chevron-down');
                chevron.className = 'example-chevron';
                title.appendChild(chevron);

                // Wrap all siblings after title into .example-content
                var content = document.createElement('div');
                content.className = 'example-content';
                while (title.nextSibling) {
                    content.appendChild(title.nextSibling);
                }
                example.appendChild(content);

                // Determine storage key from title text
                var storageKey = 'cf-ex:' + pageKey + ':' + (title.textContent.trim() || idx);
                var savedState = localStorage.getItem(storageKey);

                // Default to collapsed if no saved state
                var startCollapsed = savedState === null || savedState === 'collapsed';
                if (startCollapsed) {
                    content.style.height = '0';
                    example.classList.add('example-collapsed');
                } else {
                    content.style.height = 'auto';
                    example.classList.remove('example-collapsed');
                }

                // Track pending animation timer to prevent race conditions
                var pendingTimer = null;

                title.addEventListener('click', function () {
                    // Cancel any in-progress animation
                    if (pendingTimer !== null) {
                        clearTimeout(pendingTimer);
                        pendingTimer = null;
                    }

                    var isCollapsed = example.classList.contains('example-collapsed');

                    if (isCollapsed) {
                        // EXPAND
                        // Ensure we start from 0 (snap if stuck mid-animation)
                        content.style.transition = 'none';
                        content.style.height = '0';
                        content.offsetHeight; // force reflow
                        content.style.transition = '';

                        // Measure natural height and animate to it
                        var targetHeight = content.scrollHeight;
                        content.style.height = targetHeight + 'px';
                        example.classList.remove('example-collapsed');

                        // After transition, set auto so content can resize
                        pendingTimer = setTimeout(function () {
                            content.style.height = 'auto';
                            pendingTimer = null;
                        }, 350); // slightly longer than CSS transition (300ms)

                        localStorage.setItem(storageKey, 'expanded');
                    } else {
                        // COLLAPSE
                        // Snap to current computed height first (in case it's 'auto')
                        content.style.transition = 'none';
                        content.style.height = content.scrollHeight + 'px';
                        content.offsetHeight; // force reflow
                        content.style.transition = '';

                        // Animate to 0
                        content.style.height = '0';
                        example.classList.add('example-collapsed');

                        pendingTimer = setTimeout(function () {
                            pendingTimer = null;
                        }, 350);

                        localStorage.setItem(storageKey, 'collapsed');
                    }
                });
            });
            // Re-render Lucide for injected chevron icons
            this.initIcons();
        }
    };
})();
