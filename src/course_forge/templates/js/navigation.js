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
        }
    };
})();
