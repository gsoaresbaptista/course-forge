import hashlib
import re

import mistune
from mistune.plugins.table import table_in_quote

from course_forge.application.renders import MarkdownRenderer


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = re.sub(r"LATEXPLACEHOLDER[a-f0-9]+N\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"BLOCKPLACEHOLDER[a-f0-9]+", "", text, flags=re.IGNORECASE)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text


def strip_heading_number(text: str) -> str:
    """Remove leading section numbers from heading text."""
    return re.sub(r"^[\d]+(?:\.[\d]+)*\s*", "", text).strip()


class CalloutMixin:
    """Mixin to provide callout rendering capabilities to Mistune renderers."""

    def block_quote(self, text: str) -> str:
        content_text = text.strip()
        if not content_text:
            return f"<blockquote>{text}</blockquote>\n"

        # Match [!type] at the beginning, possibly after <p>
        match = re.search(
            r"^<p>\[!([\w-]+)\][ \t]*(.*)", content_text, re.IGNORECASE | re.DOTALL
        )
        if not match:
            # Fallback for non-wrapped content (just in case)
            match = re.search(
                r"^\[!([\w-]+)\][ \t]*(.*)", content_text, re.IGNORECASE | re.DOTALL
            )

        if match:
            callout_type = match.group(1).lower()
            raw_remainder = match.group(2)
            remainder = raw_remainder.strip()

            # Split remainder into title (first line) and body
            # Title ends at the first newline OR first </p>
            # If it starts with newline, <br>, or </p>, it's an empty title
            if (
                raw_remainder.startswith("\n")
                or remainder.startswith("</p>")
                or remainder.startswith("<br>")
                or remainder.startswith("<br/>")
            ):
                # Case: [!type] followed immediately by newline in MD
                title = ""
                body_rest = remainder
            elif "\n" in remainder:
                title, body_rest = remainder.split("\n", 1)
            else:
                title = remainder
                body_rest = ""

            if title and "</p>" in title:
                title_parts = title.split("</p>", 1)
                title = title_parts[0].strip()
                # Put the rest of that paragraph back into the body
                if title_parts[1].strip():
                    body_rest = f"<p>{title_parts[1].strip()}</p>\n" + body_rest
            else:
                title = title.replace("<br>", "").replace("<br/>", "").strip()

            icon = self._get_callout_icon(callout_type)

            # Ensure the body starts correctly if we stripped the first paragraph's start
            if body_rest.strip() and not body_rest.strip().startswith("<"):
                # If it's just raw text that was part of the first paragraph
                if body_rest.strip().endswith("</p>"):
                    body_rest = f"<p>{body_rest.strip()}"
                else:
                    body_rest = f"<p>{body_rest.strip()}</p>"

            return (
                f'<div class="callout callout-{callout_type}">\n'
                f'  <div class="callout-title">\n'
                f'    <span class="callout-icon">{icon}</span>\n'
                f'    <span class="callout-title-inner">{title if title else ""}</span>\n'
                f"  </div>\n"
                f'  <div class="callout-content">\n{body_rest}\n  </div>\n'
                f"</div>\n"
            )

        return f"<blockquote>{text}</blockquote>\n"

    def _get_callout_icon(self, callout_type: str) -> str:
        """Returns an SVG icon for the callout type."""
        icons = {
            "note": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15.5 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5L15.5 3z"/><path d="M15 3v6h6"/><path d="M9 13h6"/><path d="M9 17h3"/></svg>',
            "abstract": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
            "info": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
            "todo": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="m9 12 2 2 4-4"/></svg>',
            "tip": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .5 2.2 1.5 3.1.7.7 1.3 1.5 1.5 2.4"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>',
            "success": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            "question": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>',
            "warning": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
            "failure": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>',
            "danger": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17.01"/></svg>',
            "bug": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m8 2 1.88 1.88"/><path d="M14.12 3.88 16 2"/><path d="M9 7.13v-1a3.003 3.003 0 1 1 6 0v1"/><path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6"/><path d="M12 20v-9"/><path d="M6.53 9C4.6 8.8 3 7.1 3 5"/><path d="M6 13H2"/><path d="M3 21c0-2.1 1.7-3.9 3.8-4"/><path d="M20.97 5c0 2.1-1.6 3.8-3.53 4"/><path d="M18 13h4"/><path d="M21 21c0-2.1-1.7-3.9-3.8-4"/></svg>',
            "example": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M12 11V7"/><path d="M9 11l3 3 3-3"/></svg>',
            "quote": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/></svg>',
        }
        return icons.get(callout_type, icons["note"])


class HeadingRenderer(CalloutMixin, mistune.HTMLRenderer):
    """Custom renderer that adds section numbers to headings and supports callouts."""

    MAX_LEVELS = 6

    def __init__(self, chapter: int | None = None):
        super().__init__(escape=False)
        self.chapter = chapter
        self.counters = [0] * self.MAX_LEVELS

    def heading(self, text: str, level: int, **attrs) -> str:
        clean_text = strip_heading_number(text)
        slug = slugify(clean_text)

        if 1 <= level <= self.MAX_LEVELS:
            self.counters[level - 1] += 1
            for i in range(level, self.MAX_LEVELS):
                self.counters[i] = 0

            parts = []
            if self.chapter is not None:
                parts.append(str(self.chapter))
            for i in range(level):
                parts.append(str(self.counters[i]))

            arabic = ".".join(parts)
            html_level = level + 1

            return (
                f'<h{html_level} id="{slug}">'
                f'<span class="heading-text">{clean_text}</span>'
                f'<span class="heading-arabic">{arabic}</span>'
                f"</h{html_level}>\n"
            )

    def block_code(self, code: str, info: str | None = None) -> str:
        lang = ""
        fragment_classes: list[str] = []
        fragment_index: str | None = None

        if info:
            info_parts = info.strip().split()
            if info_parts:
                lang = info_parts[0]
                remaining = info_parts[1:]
                i = 0
                while i < len(remaining):
                    part = remaining[i]
                    if part == "fragment":
                        fragment_classes.append("fragment")
                    elif part.startswith("index="):
                        fragment_index = part[len("index="):]
                    elif fragment_classes:  # effect keyword after 'fragment'
                        fragment_classes.append(part)
                    i += 1

        classes = ["line-numbers"]
        if lang:
            classes.append(f"language-{lang}")
        classes.extend(fragment_classes)

        class_str = " ".join(classes)
        data_lang = f' data-lang="{lang.upper()}"' if lang else ""
        data_index = f' data-fragment-index="{fragment_index}"' if fragment_index else ""
        return (
            f'<pre class="{class_str}"{data_lang}{data_index}><code class="language-{lang or "none"}">'
            f"{mistune.escape(code)}"
            f"</code></pre>\n"
        )


# Regex matching inline fragment markers like {.fragment} or {.fragment.fade-up} or {.fragment.highlight-red index=2}
_INLINE_FRAGMENT_RE = re.compile(
    r'\{\s*\.fragment(?:\.([\w-]+))?(?:\s+index=(\d+))?\s*\}'
)


class SlideRenderer(CalloutMixin, mistune.HTMLRenderer):
    """Renderer for Reveal.js slides."""

    def thematic_break(self) -> str:
        """Use horizontal rules as slide separators."""
        return "</section>\n<section>"

    def block_code(self, code: str, info: str | None = None) -> str:
        """Reuse HeadingRenderer's code block with full fragment support."""
        lang = ""
        fragment_classes: list[str] = []
        fragment_index: str | None = None

        if info:
            info_parts = info.strip().split()
            if info_parts:
                lang = info_parts[0]
                remaining = info_parts[1:]
                i = 0
                while i < len(remaining):
                    part = remaining[i]
                    if part == "fragment":
                        fragment_classes.append("fragment")
                    elif part.startswith("index="):
                        fragment_index = part[len("index="):]
                    elif fragment_classes:
                        fragment_classes.append(part)
                    i += 1

        classes = ["line-numbers"]
        if lang:
            classes.append(f"language-{lang}")
        classes.extend(fragment_classes)

        class_str = " ".join(classes)
        data_lang = f' data-lang="{lang.upper()}"' if lang else ""
        data_index = f' data-fragment-index="{fragment_index}"' if fragment_index else ""
        return (
            f'<pre class="{class_str}"{data_lang}{data_index}><code class="language-{lang or "none"}">'
            f"{mistune.escape(code)}"
            f"</code></pre>\n"
        )

    def list_item(self, text: str, **attrs) -> str:
        """Support inline {.fragment} / {.fragment.effect index=N} markers on list items."""
        # Strip trailing </p>\n to get the inner content, then re-wrap
        match = _INLINE_FRAGMENT_RE.search(text)
        if match:
            effect = match.group(1)  # may be None
            idx = match.group(2)     # may be None
            # Remove the marker from the text
            clean = _INLINE_FRAGMENT_RE.sub("", text).strip()
            classes = ["fragment"]
            if effect:
                classes.append(effect)
            class_str = " ".join(classes)
            data_index = f' data-fragment-index="{idx}"' if idx else ""
            return f'<li class="{class_str}"{data_index}>{clean}</li>\n'
        return f"<li>{text}</li>\n"


class MistuneMarkdownRenderer(MarkdownRenderer):
    COMMENT_PATTERN = re.compile(r"%%[\s\S]*?%%", re.MULTILINE)

    def render(self, text: str, chapter: int | None = None) -> str:
        text, latex_placeholders = self._preprocess_latex(text)
        text, block_placeholders = self._preprocess_block_divs(text)
        text, fragment_placeholders = self._preprocess_fragment_containers(text)

        # Fix nested emphasis ambiguity (e.g. **bold *italic*** -> **bold _italic_**)
        # Mistune v3 sometimes gets confused with triple asterisks at the end of nested spans.
        # We replace the internal single * with _ which is semantically equivalent in MD.
        text = re.sub(r'(\*\*)([^*]+?)\*([^*]+?)\*(\*\*)', r'\1\2_\3_\4', text)

        renderer = HeadingRenderer(chapter=chapter)
        markdown = mistune.create_markdown(
            renderer=renderer,
            hard_wrap=True,
            plugins=["table", "strikethrough", table_in_quote, self._obsidian_comments_plugin],
        )
        html = str(markdown(text))

        # Restore block divs (renders inner markdown)
        html = self._restore_block_divs(html, block_placeholders, False, chapter)
        # Restore fragments
        html = self._restore_fragment_containers(html, fragment_placeholders, False, chapter)
        # Restore LaTeX after markdown processing
        html = self._restore_placeholders(html, latex_placeholders)
        return html

    def render_slide(self, text: str) -> str:
        """Render markdown content as Reveal.js slides."""
        text, latex_placeholders = self._preprocess_latex(text)
        text, block_placeholders = self._preprocess_block_divs(text)
        text, fragment_placeholders = self._preprocess_fragment_containers(text)

        renderer = SlideRenderer(escape=False)
        markdown = mistune.create_markdown(
            renderer=renderer,
            hard_wrap=True,
            plugins=["table", "strikethrough", table_in_quote, self._obsidian_comments_plugin],
        )
        html = str(markdown(text))

        # Wrap in initial section tags if not empty
        if html.strip():
            if not html.startswith("<section>"):
                html = f"<section>{html}</section>"
        else:
            html = "<section></section>"

        html = self._restore_block_divs(html, block_placeholders, True)
        html = self._restore_fragment_containers(html, fragment_placeholders, True)
        html = self._restore_placeholders(html, latex_placeholders)
        return html

    def _strip_comments(self, text: str) -> str:
        """Deprecated: Comments are now handled by Mistune plugin."""
        return text

    def _preprocess_latex(self, text: str) -> tuple[str, dict[str, str]]:
        """
        Protect LaTeX from modification and handle escaped dollar signs.
        """
        latex_placeholders: dict[str, str] = {}
        counter = 0

        # Pattern to match code blocks (to ignore), LaTeX blocks/inline, and escaped dollars
        pattern = re.compile(
            r"(?P<code>```[\s\S]*?```|`[^`\n]+`)|"
            r"(?P<latex_block>\$\$[\s\S]*?\$\$)|"
            r"(?P<latex_inline>(?<!\\)(?<!\$)\$(?!\$)(?P<content>[^$\n]+?)(?<!\\)(?<!\$)\$(?!\$))|"
            r"(?P<escaped_dollar>\\\$)",
            re.MULTILINE,
        )

        def replace_fn(match: re.Match) -> str:
            nonlocal counter

            # If it's code, mask pipes and return it
            if match.groupdict().get("code"):
                content = match.group(0)
                if "|" in content:
                    return content.replace("|", "\ufffe")
                return content

            # If it's an escaped dollar, convert to span to avoid KaTeX
            if match.groupdict().get("escaped_dollar"):
                return "<span>$</span>"

            # Create a deterministic placeholder for LaTeX (based on content hash)
            content_hash = hashlib.md5(match.group(0).encode()).hexdigest()
            placeholder = f"LATEXPLACEHOLDER{content_hash}N{counter}"
            latex_placeholders[placeholder] = match.group(0)
            counter += 1
            return placeholder

        # Mask pipes in bold/italic to avoid breaking table rendering.
        # We must skip code spans (backticks) so that * or _ inside code
        # are not mistaken for emphasis delimiters.
        text = pattern.sub(replace_fn, text)
        _emphasis_pipe_re = re.compile(
            r"`[^`\n]+`"           # code span — skip entirely
            r"|(\*\*|__)"          # bold delimiter (group 1)
            r"|(\*|_)"            # italic delimiter (group 2)
        )

        def _mask_emphasis_pipes(line: str) -> str:
            """Mask pipes inside bold/italic spans on a single line."""
            # Only process lines that look like they could have emphasis around pipes
            if "|" not in line:
                return line

            # Find all emphasis delimiters (skipping code spans)
            delimiters = []
            for m in _emphasis_pipe_re.finditer(line):
                if m.group(1):  # bold
                    delimiters.append((m.start(), m.end(), m.group(1), "bold"))
                elif m.group(2):  # italic
                    delimiters.append((m.start(), m.end(), m.group(2), "italic"))
                # code spans are matched but not appended, so they're skipped

            # Pair up matching delimiters and mask pipes between them
            result = list(line)
            used = set()
            for i, (s1, e1, d1, t1) in enumerate(delimiters):
                if i in used:
                    continue
                # Find matching closing delimiter of same type
                for j in range(i + 1, len(delimiters)):
                    if j in used:
                        continue
                    s2, e2, d2, t2 = delimiters[j]
                    if d1 == d2 and t1 == t2:
                        # Mask pipes between these delimiters
                        for k in range(e1, s2):
                            if result[k] == "|":
                                result[k] = "\ufffe"
                        used.add(i)
                        used.add(j)
                        break
            return "".join(result)

        text = "\n".join(_mask_emphasis_pipes(l) for l in text.split("\n"))

        return text, latex_placeholders

    def _restore_placeholders(self, text: str, placeholders: dict[str, str]) -> str:
        """Restore protected blocks from placeholders."""
        # Restore masked pipes
        text = text.replace("\ufffe", "|")

        # Sort descending by length so longer placeholders (like ...N10) are
        # completely replaced before smaller substring placeholders (like ...N1)
        for placeholder, original in sorted(placeholders.items(), key=lambda x: len(x[0]), reverse=True):
            text = text.replace(placeholder, original)
        return text

    # Regex to find opening block tags (example, exam, assignment, slide, etc.)
    _BLOCK_OPEN_RE = re.compile(
        r'<(?P<tag>div|span)\b[^>]*?(?:class="(?:example|exam|assignment|question|questions|block-slide|block-presentation)"|markdown="(?:1|true)")[^>]*>', 
        re.IGNORECASE
    )
    _BLOCK_TITLE_RE = re.compile(
        r'<div\s+class="[\w-]+-title">(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )

    # Regex to find fragment containers: ::: fragment [effect] [index=N]
    # Also matches ::: fragment list [effect] [index=N] for per-item fragments
    _FRAGMENT_CONTAINER_RE = re.compile(r':::[ \t]*fragment(?:[ \t]+([^\n]*))?[ \t]*\n(.*?)\n:::[ \t]*', re.DOTALL)

    # Valid Reveal.js fragment animation classes
    _FRAGMENT_EFFECTS = {
        "fade-out", "fade-up", "fade-down", "fade-left", "fade-right",
        "fade-in-then-out", "fade-in-then-semi-out",
        "grow", "shrink", "strike",
        "highlight-red", "highlight-green", "highlight-blue",
        "highlight-current-red", "highlight-current-green", "highlight-current-blue",
        "semi-fade-out", "current-visible",
    }

    def _preprocess_block_divs(
        self, text: str
    ) -> tuple[str, dict[str, str]]:
        """Replace block html tags with placeholders before Mistune.

        Uses depth tracking to correctly handle nested tags and is code-aware.
        """
        placeholders: dict[str, str] = {}
        result = []
        pos = 0

        # Pattern to match code blocks (to ignore) and block openings
        pattern = re.compile(
            r"(?P<code>```[\s\S]*?```|`[^`\n]+`)|"
            r"(?P<open><(?P<tag>div|span)\b[^>]*?(?:class=\"(?:example|exam|assignment|question|questions|block-slide|block-presentation)\"|markdown=\"(?:1|true)\")[^>]*>)",
            re.IGNORECASE | re.MULTILINE
        )

        while pos < len(text):
            match = pattern.search(text, pos)
            if not match:
                result.append(text[pos:])
                break

            # Append everything before this match
            result.append(text[pos:match.start()])

            if match.group("code"):
                result.append(match.group(0))
                pos = match.end()
                continue

            # Found an opening tag
            tag_name = match.group("tag").lower()
            
            # Find the matching closing tag by counting depth, skipping code blocks inside
            depth = 1
            search_pos = match.end()
            
            # Sub-pattern for finding next open/close or code block
            sub_pattern = re.compile(
                r"(?P<code>```[\s\S]*?```|`[^`\n]+`)|"
                rf"(?P<open><{tag_name}[\s>])|"
                rf"(?P<close></{tag_name}>)",
                re.IGNORECASE | re.MULTILINE
            )

            while depth > 0 and search_pos < len(text):
                sub_match = sub_pattern.search(text, search_pos)
                if not sub_match:
                    # No more tags — malformed, take rest
                    break

                if sub_match.group("code"):
                    search_pos = sub_match.end()
                    continue
                
                if sub_match.group("open"):
                    depth += 1
                    search_pos = sub_match.end()
                elif sub_match.group("close"):
                    depth -= 1
                    if depth == 0:
                        # Found the matching </div>
                        full_block = text[match.start():sub_match.end()]
                        content_hash = hashlib.md5(full_block.encode()).hexdigest()
                        placeholder = f"BLOCKPLACEHOLDER{content_hash}"
                        placeholders[placeholder] = full_block
                        # Surround with blank lines
                        result.append(f"\n\n{placeholder}\n\n")
                        pos = sub_match.end()
                        break
                    search_pos = sub_match.end()
            else:
                # Couldn't find matching close, skip this match
                result.append(match.group(0))
                pos = match.end()
                continue

        return "".join(result), placeholders

    def _restore_block_divs(
        self, html: str, placeholders: dict[str, str], is_slide: bool = False, chapter: int | None = None
    ) -> str:
        """Restore block div placeholders, rendering inner markdown."""
        for placeholder, original in placeholders.items():
            open_match = self._BLOCK_OPEN_RE.match(original)
            if not open_match:
                # Fallback, just return unchanged if somehow pattern misses
                html = html.replace(placeholder, original)
                continue
                
            open_tag = open_match.group(0)
            tag_name = open_match.group("tag").lower()
            close_tag = f"</{tag_name}>"

            # Extract title
            title_match = self._BLOCK_TITLE_RE.search(original, open_match.end())
            title_html = ""
            inner_md = original
            
            if title_match:
                title_html = title_match.group(0)
                # Content is everything after the title div, before the closing tag
                after_title = original[title_match.end():]
                # Remove the trailing closing tag
                if after_title.rstrip().endswith(close_tag):
                    after_title = after_title.rstrip()[:-len(close_tag)]
                inner_md = after_title
            else:
                # No title — strip outer open_tag and close_tag
                inner_md = original[open_match.end():]
                if inner_md.rstrip().endswith(close_tag):
                    inner_md = inner_md.rstrip()[:-len(close_tag)]

            # Render the inner content as markdown
            inner_md = inner_md.strip()
            if inner_md:
                inner_html = self._render_inner_markdown(inner_md, is_slide, chapter)
            else:
                inner_html = ""

            restored = f"{open_tag}\n"
            if title_html:
                restored += f"  {title_html}\n"
            if inner_html:
                # remove trailing newline from inner_html to keep things tidy
                restored += f"  {inner_html.rstrip()}\n"
            restored += f"{close_tag}"
            
            # Mistune often wraps block placeholders with <p> since they are just text between blank lines.
            p_wrapped = rf"<p>\s*{placeholder}\s*</p>"
            if re.search(p_wrapped, html):
                html = re.sub(p_wrapped, restored, html)
            else:
                html = html.replace(placeholder, restored)
        return html

    def _unwrap_single_paragraph(self, html: str) -> str:
        """Remove <p> tags if the html is exactly one paragraph."""
        stripped = html.strip()
        if stripped.startswith('<p>') and stripped.endswith('</p>'):
            if stripped.count('<p>') == 1 and stripped.count('</p>') == 1:
                return stripped[3:-4].strip()
        return html

    def _render_inner_markdown(self, text: str, is_slide: bool = False, chapter: int | None = None) -> str:
        """Render a markdown fragment (used for example div content)."""
        text, latex_ph = self._preprocess_latex(text)
        text, fragment_ph = self._preprocess_fragment_containers(text)

        renderer = SlideRenderer(escape=False) if is_slide else HeadingRenderer(chapter=chapter)
        md = mistune.create_markdown(
            renderer=renderer,
            hard_wrap=True,
            plugins=["table", "strikethrough", table_in_quote, self._obsidian_comments_plugin],
        )
        html = str(md(text))
        html = self._restore_fragment_containers(html, fragment_ph, is_slide, chapter)
        html = self._restore_placeholders(html, latex_ph)
        return self._unwrap_single_paragraph(html)

    def _preprocess_fragment_containers(self, text: str) -> tuple[str, dict]:
        """Extract ::: fragment blocks and replace them with placeholders."""
        placeholders: dict[str, tuple] = {}
        counter = 0

        # Pattern to match code blocks (to ignore) and fragments
        pattern = re.compile(
            r"(?P<code>```[\s\S]*?```|`[^`\n]+`)|"
            r"(?P<fragment>^[ \t]*:::[ \t]*fragment(?P<opts_raw>[ \t]+[^\n]*)?[ \t]*\n(?P<content>.*?)\n^[ \t]*:::[ \t]*$)",
            re.MULTILINE | re.DOTALL
        )

        def replace_fragment(match):
            nonlocal counter
            if match.group("code"):
                return match.group(0)

            opts_raw = match.group("opts_raw").strip() if match.group("opts_raw") else ""
            content = match.group("content")

            # Parse options: detect 'list' keyword, effect, and index=N
            opts_parts = opts_raw.split() if opts_raw else []
            is_list = False
            effect: str | None = None
            index: str | None = None

            for part in opts_parts:
                if part == "list":
                    is_list = True
                elif part.startswith("index="):
                    index = part[len("index="):]
                elif part in self._FRAGMENT_EFFECTS:
                    effect = part
                else:
                    effect = part

            content_hash = hashlib.md5(content.encode()).hexdigest()
            placeholder = f"FRAGMENTPLACEHOLDER{content_hash}N{counter}"
            counter += 1
            placeholders[placeholder] = (effect, index, is_list, content)
            
            # Surround with blank lines to avoid being eaten by setext headings (---)
            return f"\n\n{placeholder}\n\n"

        new_text = pattern.sub(replace_fragment, text)
        return new_text, placeholders

    def _restore_fragment_containers(
        self, html: str, placeholders: dict, is_slide: bool = False, chapter: int | None = None
    ) -> str:
        """Restore fragment placeholders with rendered HTML."""
        for placeholder, (effect, index, is_list, content) in placeholders.items():
            inner_html = self._render_inner_markdown(content, is_slide, chapter)

            data_index = f' data-fragment-index="{index}"' if index else ""

            if is_list:
                # Wrap each <li> inside the inner HTML with fragment classes
                classes = ["fragment"]
                if effect:
                    classes.append(effect)
                class_str = " ".join(classes)

                def add_fragment_to_li(m):
                    existing_attrs = m.group(1).strip() if m.group(1) else ""
                    # Merge with existing class if present
                    if 'class="' in existing_attrs:
                        new_attrs = re.sub(
                            r'class="([^"]*)"',
                            lambda cm: f'class="{cm.group(1)} {class_str}"',
                            existing_attrs,
                        )
                    else:
                        new_attrs = (existing_attrs + f' class="{class_str}"').strip()
                    return f'<li {new_attrs}{data_index}>'

                replacement = re.sub(r'<li([^>]*)>', add_fragment_to_li, inner_html)
            else:
                classes = ["fragment"]
                if effect:
                    classes.append(effect)
                class_str = " ".join(classes)
                replacement = (
                    f'<div class="{class_str}"{data_index}>\n'
                    f'  {inner_html.rstrip()}\n'
                    f'</div>'
                )

            p_wrapped = rf"<p>\s*{placeholder}\s*</p>"
            if re.search(p_wrapped, html):
                html = re.sub(p_wrapped, replacement, html)
            else:
                html = html.replace(placeholder, replacement)
        return html

    @staticmethod
    def _obsidian_comments_plugin(markdown):
        """Mistune plugin to strip Obsidian comments (%% ... %%)."""
        COMMENT_PATTERN = r"%%[\s\S]*?%%"

        def parse_comment(inline, m, state):
            # Return ('comment', '') to indicate successful parsing but empty content
            return "comment", ""

        # Mistune v3 syntax: register(name, pattern, func)
        markdown.inline.register("obsidian_comment", COMMENT_PATTERN, parse_comment)
