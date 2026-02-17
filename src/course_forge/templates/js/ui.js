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
         * adds a chevron icon, and starts collapsed.
         */
        initExamples: function () {
            const examples = document.querySelectorAll('.example');
            examples.forEach(example => {
                const title = example.querySelector('.example-title');
                if (!title || title.dataset.initialized) return;
                title.dataset.initialized = 'true';

                // Add chevron icon to title
                const chevron = document.createElement('i');
                chevron.setAttribute('data-lucide', 'chevron-down');
                chevron.className = 'example-chevron';
                title.appendChild(chevron);

                // Wrap all siblings after title into .example-content
                const content = document.createElement('div');
                content.className = 'example-content';
                while (title.nextSibling) {
                    content.appendChild(title.nextSibling);
                }
                example.appendChild(content);

                // Start collapsed
                content.style.height = '0';
                example.classList.add('example-collapsed');

                // Toggle on title click
                title.addEventListener('click', () => {
                    const isCollapsed = example.classList.contains('example-collapsed');
                    if (isCollapsed) {
                        // Expand: measure natural height, animate to it
                        content.style.height = content.scrollHeight + 'px';
                        example.classList.remove('example-collapsed');
                        // After transition, set auto so it resizes with content
                        const onEnd = () => {
                            content.style.height = 'auto';
                            content.removeEventListener('transitionend', onEnd);
                        };
                        content.addEventListener('transitionend', onEnd);
                    } else {
                        // Collapse: set explicit height first, then animate to 0
                        content.style.height = content.scrollHeight + 'px';
                        // Force reflow
                        content.offsetHeight;
                        content.style.height = '0';
                        example.classList.add('example-collapsed');
                    }
                });
            });
            // Re-render Lucide for injected chevron icons
            this.initIcons();
        }
    };
})();
