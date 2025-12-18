# Course Forge

Course Forge is a static site generator (SSG) designed for academic content, allowing instructors to build beautiful, structured courses and share common modules across disciplines easily.

## Key Features

-   **Markdown-First**: Write your content in standard Markdown and let Course Forge handle the rest.
-   **Structured Navigation**: Automatic generation of Tables of Contents (TOC), breadcrumbs, and discipline indexes.
-   **Symbolic Modules**: Share modules/folders between different courses without duplicating files.
-   **Content Processors**:
    -   **Digital Circuits**: Render SVG diagrams of digital circuits with a custom "sketch" hand-drawn effect.
    -   **AST Rendering**: Visualize Abstract Syntax Trees.
    -   **LaTeX Support**: Built-in MathJax/KaTeX integration for beautiful mathematical formulas.
    -   **Internal Links**: Smart resolution of links between different modules and topics.
    -   **Download Management**: Automatic handling and marking of downloadable assets.
-   **Slides**: Convert Markdown files into Reveal.js presentations by simply adding `type: slide` to the frontmatter.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/gabriel/course-forge.git
cd course-forge

# Install dependencies
uv sync
```

## Quick Start

To build your site:

```bash
uv run course-forge build -c /path/to/content -o /path/to/output
```

To watch for changes and serve locally:

```bash
uv run course-forge watch -c /path/to/content -o /path/to/output --port 8000
```

## Project Structure

```text
content/
├── config.yaml          # Global site configuration
├── shared/              # Central location for shared modules
│   └── logic-intro/
│       ├── config.yaml  # Set 'hidden: true' to hide from main index
│       └── topic1.md
└── discipline-a/
    └── intro/
        └── config.yaml  # Set 'source: ../../shared/logic-intro'
```

## Configuration

### Global Config (`config.yaml` at root)

```yaml
site_name: My Academic Portal
courses_title: Disciplinas
author: Prof. John Doe
```

### Module Config (`config.yaml` in module folders)

-   `name`: Custom display name for the module.
-   `hidden`: (boolean) If `true`, the module won't appear in the main index list.
-   `source`: (string) Path to another directory to load content from (Symbolic Module).

### Markdown Frontmatter

```markdown
---
title: My Great Topic
type: slide  # Optional: renders as Reveal.js slides
---

# Content starts here...
```

## Symbolic Modules Example

If you want to share a "Compilers Overview" module between two different courses:

1.  Place the content in `content/shared/compilers-overview/`.
2.  Add `hidden: true` to its `config.yaml`.
3.  In Course A and Course B folders, create a subfolder and add a `config.yaml` with:
    ```yaml
    source: ../../shared/compilers-overview
    name: Compilers Introduction
    ```

## Technology Stack

-   **Core**: Python
-   **Templating**: Jinja2
-   **Markdown**: Mistune
-   **Styling**: Vanilla CSS with modern aesthetics
-   **JavaScript**: Reveal.js (slides), Rough.js (sketch effect), KaTeX (math)
