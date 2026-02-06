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
        }
    };
})();
