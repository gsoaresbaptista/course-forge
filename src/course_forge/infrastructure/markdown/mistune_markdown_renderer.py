import hashlib
import re

import mistune
from mistune.plugins.table import table_in_quote

from course_forge.application.renders import MarkdownRenderer


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = re.sub(r"LATEXPLACEHOLDER[a-f0-9]+N\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"EXAMPLEPLACEHOLDER[a-f0-9]+", "", text, flags=re.IGNORECASE)
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
        if info:
            lang = info.strip().split(None, 1)[0]

        classes = ["line-numbers"]
        if lang:
            classes.append(f"language-{lang}")

        class_str = " ".join(classes)
        data_lang = f' data-lang="{lang.upper()}"' if lang else ""
        return (
            f'<pre class="{class_str}"{data_lang}><code class="language-{lang or "none"}">'
            f"{mistune.escape(code)}"
            f"</code></pre>\n"
        )


class SlideRenderer(CalloutMixin, mistune.HTMLRenderer):
    """Renderer for Reveal.js slides."""

    def thematic_break(self) -> str:
        """Use horizontal rules as slide separators."""
        return "</section>\n<section>"


class MistuneMarkdownRenderer(MarkdownRenderer):
    COMMENT_PATTERN = re.compile(r"%%[\s\S]*?%%", re.MULTILINE)

    def render(self, text: str, chapter: int | None = None) -> str:
        text, latex_placeholders = self._preprocess_latex(text)
        text, example_placeholders = self._preprocess_example_divs(text)

        renderer = HeadingRenderer(chapter=chapter)
        markdown = mistune.create_markdown(
            renderer=renderer,
            plugins=["table", "strikethrough", table_in_quote, self._obsidian_comments_plugin],
        )
        html = str(markdown(text))

        # Restore example divs (renders inner markdown)
        html = self._restore_example_divs(html, example_placeholders, chapter)
        # Restore LaTeX after markdown processing
        html = self._restore_placeholders(html, latex_placeholders)
        return html

    def render_slide(self, text: str) -> str:
        """Render markdown content as Reveal.js slides."""
        text, latex_placeholders = self._preprocess_latex(text)

        renderer = SlideRenderer(escape=False)
        markdown = mistune.create_markdown(
            renderer=renderer,
            plugins=["table", "strikethrough", table_in_quote, self._obsidian_comments_plugin],
        )
        html = str(markdown(text))

        # Wrap in initial section tags if not empty
        if html.strip():
            if not html.startswith("<section>"):
                html = f"<section>{html}</section>"
        else:
            html = "<section></section>"

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

        for placeholder, original in placeholders.items():
            text = text.replace(placeholder, original)
        return text

    # Regex to find opening <div class="example"> tags
    _EXAMPLE_OPEN_RE = re.compile(r'<div\s+class="example">', re.DOTALL)
    _EXAMPLE_TITLE_RE = re.compile(
        r'<div\s+class="example-title">(.*?)</div>',
        re.DOTALL,
    )

    def _preprocess_example_divs(
        self, text: str
    ) -> tuple[str, dict[str, str]]:
        """Replace <div class='example'> blocks with placeholders before Mistune.

        Uses depth tracking to correctly handle nested <div> tags.
        """
        placeholders: dict[str, str] = {}
        result = []
        pos = 0

        while pos < len(text):
            match = self._EXAMPLE_OPEN_RE.search(text, pos)
            if not match:
                result.append(text[pos:])
                break

            # Append everything before this match
            result.append(text[pos:match.start()])

            # Find the matching </div> by counting depth
            depth = 1
            search_pos = match.end()
            div_open = re.compile(r'<div[\s>]', re.IGNORECASE)
            div_close = re.compile(r'</div>', re.IGNORECASE)

            while depth > 0 and search_pos < len(text):
                next_open = div_open.search(text, search_pos)
                next_close = div_close.search(text, search_pos)

                if next_close is None:
                    # No more closing tags — malformed, take rest
                    break

                if next_open and next_open.start() < next_close.start():
                    depth += 1
                    search_pos = next_open.end()
                else:
                    depth -= 1
                    if depth == 0:
                        # Found the matching </div>
                        full_block = text[match.start():next_close.end()]
                        content_hash = hashlib.md5(full_block.encode()).hexdigest()
                        placeholder = f"EXAMPLEPLACEHOLDER{content_hash}"
                        placeholders[placeholder] = full_block
                        result.append(placeholder)
                        pos = next_close.end()
                        break
                    search_pos = next_close.end()
            else:
                # Couldn't find matching close, skip this match
                result.append(match.group(0))
                pos = match.end()
                continue

        return "".join(result), placeholders

    def _restore_example_divs(
        self, html: str, placeholders: dict[str, str], chapter: int | None = None
    ) -> str:
        """Restore example div placeholders, rendering inner markdown."""
        for placeholder, original in placeholders.items():
            # Extract title
            title_match = self._EXAMPLE_TITLE_RE.search(original)
            title_html = ""
            inner_md = original
            if title_match:
                title_html = title_match.group(0)
                # Content is everything after the title div, before the closing </div>
                after_title = original[title_match.end():]
                # Remove the trailing </div> that closes the example div
                if after_title.rstrip().endswith("</div>"):
                    after_title = after_title.rstrip()[:-len("</div>")]
                inner_md = after_title
            else:
                # No title — strip outer <div class="example"> and </div>
                inner_md = self._EXAMPLE_OPEN_RE.sub("", original, count=1)
                if inner_md.rstrip().endswith("</div>"):
                    inner_md = inner_md.rstrip()[:-len("</div>")]

            # Render the inner content as markdown
            inner_md = inner_md.strip()
            if inner_md:
                inner_html = self._render_inner_markdown(inner_md, chapter)
            else:
                inner_html = ""

            restored = (
                f'<div class="example">\n'
                f"  {title_html}\n"
                f"  {inner_html}\n"
                f"</div>"
            )
            html = html.replace(placeholder, restored)
        return html

    def _render_inner_markdown(self, text: str, chapter: int | None = None) -> str:
        """Render a markdown fragment (used for example div content)."""
        text, latex_ph = self._preprocess_latex(text)
        renderer = HeadingRenderer(chapter=chapter)
        md = mistune.create_markdown(
            renderer=renderer,
            plugins=["table", "strikethrough", table_in_quote, self._obsidian_comments_plugin],
        )
        html = str(md(text))
        html = self._restore_placeholders(html, latex_ph)
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
