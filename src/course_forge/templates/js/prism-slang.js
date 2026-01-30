/* Slang Language Grammar for Prism.js */
(function () {
    // Wait for Prism to be available (loaded from CDN)
    function registerSlang() {
        if (typeof Prism === 'undefined') {
            // Prism not loaded yet, try again shortly
            setTimeout(registerSlang, 50);
            return;
        }

        Prism.languages.slang = {
            'comment': [
                {
                    pattern: /(^|[^\\])\/\*[\s\S]*?(?:\*\/|$)/,
                    lookbehind: true,
                    greedy: true
                },
                {
                    pattern: /(^|[^\\:])\/\/.*/,
                    lookbehind: true,
                    greedy: true
                }
            ],
            'string': {
                pattern: /(["'])(?:\\(?:\r\n|[\s\S])|(?!\1)[^\\\r\n])*\1/,
                greedy: true
            },
            'class-name': {
                pattern: /(\b(?:fn)\s+)\w+/,
                lookbehind: true
            },
            'keyword': /\b(?:if|else|loop|while|for|fn|return|true|false|int|bool|float|char|string|void|and|or|not)\b/,
            'boolean': /\b(?:true|false)\b/,
            'function': /\b\w+(?=\()/,
            'number': /\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b/i,
            'operator': /->|[-+]{1,2}|!|<=?|>=?|={1,3}|&{1,2}|\|{1,2}|\?|\*|\/|%|\^|~/,
            'punctuation': /[{}[\];(),.:]/
        };

        // Re-highlight if page is already loaded
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            Prism.highlightAll();
        }
    }

    // Start checking for Prism
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', registerSlang);
    } else {
        registerSlang();
    }
})();
