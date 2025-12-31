/**
 * navigation.js - Context-aware navigation for Course Forge.
 */

window.CourseForgeNav = (function () {
    const STORAGE_KEY_URL = 'cf_last_course_url';
    const STORAGE_KEY_NAME = 'cf_last_course_name';

    return {
        /**
         * Store the current course context if it's a main course.
         */
        storeContext: function (name, url, isSubcourse) {
            if (!isSubcourse) {
                // Ensure URL is absolute for consistency
                const absoluteUrl = new URL(url, window.location.href).pathname;
                sessionStorage.setItem(STORAGE_KEY_URL, absoluteUrl);
                sessionStorage.setItem(STORAGE_KEY_NAME, name);
            }
        },

        /**
         * Get the dynamic back link.
         */
        getBackLink: function (defaultUrl, defaultText, isSubcourse) {
            const lastUrl = sessionStorage.getItem(STORAGE_KEY_URL);
            const lastName = sessionStorage.getItem(STORAGE_KEY_NAME);

            if (isSubcourse && lastUrl) {
                return {
                    url: lastUrl,
                    text: 'Voltar para ' + lastName
                };
            }

            return {
                url: defaultUrl,
                text: defaultText
            };
        },

        /**
         * Update a link element with dynamic context.
         */
        applyDynamicBackLink: function (selector, defaultUrl, defaultText, isSubcourse) {
            const link = document.querySelector(selector);
            if (!link) return;

            const dynamic = this.getBackLink(defaultUrl, defaultText, isSubcourse);
            link.href = dynamic.url;

            // preserved arrow if it exists in original text
            if (link.textContent.includes('←')) {
                link.textContent = '← ' + dynamic.text;
            } else {
                link.textContent = dynamic.text;
            }
        },

        /**
         * Prepend parent course to breadcrumbs if in a sub-course context.
         */
        applyDynamicBreadcrumbs: function (selector, isSubcourse) {
            const container = document.querySelector(selector);
            if (!container || !isSubcourse) return;

            const lastUrl = sessionStorage.getItem(STORAGE_KEY_URL);
            const lastName = sessionStorage.getItem(STORAGE_KEY_NAME);

            if (lastUrl && lastName) {
                // Check if already present as first crumb to avoid duplicates
                const firstCrumb = container.querySelector('.breadcrumb-link, .breadcrumb-part');
                if (firstCrumb && firstCrumb.textContent.trim().toLowerCase() === lastName.trim().toLowerCase()) {
                    return;
                }

                // Create the new crumb
                const crumb = document.createElement('a');
                crumb.href = lastUrl;
                crumb.className = 'breadcrumb-link';
                crumb.textContent = lastName;

                const separator = document.createElement('span');
                separator.className = 'breadcrumb-separator';
                separator.textContent = ' › ';

                // Insert at the beginning
                container.insertBefore(separator, container.firstChild);
                container.insertBefore(crumb, container.firstChild);
            }
        },

        /**
         * Toggle sidebar visibility and store state.
         */
        toggleSidebar: function () {
            const body = document.body;
            const isHidden = body.classList.toggle('sidebar-hidden');
            localStorage.setItem('cf_sidebar_hidden', isHidden);
        },

        /**
         * Initialize sidebar state from localStorage.
         */
        initSidebar: function () {
            const isHidden = localStorage.getItem('cf_sidebar_hidden') === 'true';
            if (isHidden) {
                document.body.classList.add('sidebar-hidden');
            }
        },

        /**
         * Initialize ScrollSpy for Table of Contents highlighting.
         */
        initScrollSpy: function () {
            const tocLinks = document.querySelectorAll('.toc-item a');
            if (tocLinks.length === 0) return;

            const sections = [];
            let isScrollingFromClick = false;
            let scrollEndTimer = null;

            tocLinks.forEach(link => {
                const id = link.getAttribute('href').substring(1);
                const element = document.getElementById(id);
                if (element) {
                    sections.push({ id, link: link.parentElement, element });
                }
            });

            function updateActive() {
                if (isScrollingFromClick) return;

                const scrollPos = window.scrollY;
                const windowHeight = window.innerHeight;
                const bodyHeight = document.body.offsetHeight;
                let activeSection = null;

                // Edge case: At the very top
                if (scrollPos < 100 && sections.length > 0) {
                    activeSection = sections[0];
                }
                // Edge case: At the very bottom
                else if (scrollPos + windowHeight >= bodyHeight - 50 && sections.length > 0) {
                    activeSection = sections[sections.length - 1];
                }
                else {
                    // Find the section that is currently most visible or just passed the top
                    // We use an offset of 100px to account for headers
                    const offset = 120;
                    for (let i = 0; i < sections.length; i++) {
                        const section = sections[i];
                        if (section.element.offsetTop - offset <= scrollPos) {
                            activeSection = section;
                        } else {
                            break;
                        }
                    }
                }

                if (activeSection) {
                    sections.forEach(s => s.link.classList.remove('active'));
                    activeSection.link.classList.add('active');

                    // Sync sidebar scroll
                    const sidebarToc = document.querySelector('.toc-list');
                    if (sidebarToc) {
                        const linkRect = activeSection.link.getBoundingClientRect();
                        const tocRect = sidebarToc.getBoundingClientRect();
                        if (linkRect.top < tocRect.top || linkRect.bottom > tocRect.bottom) {
                            activeSection.link.scrollIntoView({ behavior: 'auto', block: 'nearest' });
                        }
                    }
                }
            }

            window.addEventListener('scroll', updateActive, { passive: true });

            // Handle clicks for immediate feedback
            tocLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    isScrollingFromClick = true;
                    if (scrollEndTimer) clearTimeout(scrollEndTimer);

                    sections.forEach(s => s.link.classList.remove('active'));
                    link.parentElement.classList.add('active');

                    // Resume ScrollSpy after smooth scroll finishes (approx 1s)
                    scrollEndTimer = setTimeout(() => {
                        isScrollingFromClick = false;
                    }, 1000);
                });
            });

            // Initial run
            updateActive();
        },

        /**
         * Initialize copy buttons for code blocks.
         */
        initCopyButtons: function () {
            const preBlocks = document.querySelectorAll('pre[class*="language-"]');
            preBlocks.forEach(pre => {
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
                        // Try modern API first
                        if (navigator.clipboard && window.isSecureContext) {
                            await navigator.clipboard.writeText(text);
                            success = true;
                        } else {
                            // Fallback for insecure contexts or older browsers
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
                            button.innerHTML = '<i data-lucide="check" style="color: #4ade80;"></i>';
                            if (typeof lucide !== 'undefined') lucide.createIcons();

                            setTimeout(() => {
                                button.innerHTML = '<i data-lucide="copy"></i>';
                                if (typeof lucide !== 'undefined') lucide.createIcons();
                            }, 2000);
                        }
                    } catch (err) {
                        console.error('Failed to copy: ', err);
                    }
                });
            });

            // Initial Lucide pass for injected buttons
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
    };
})();
