# Como Restaurar o Tema Clássico

Este diretório contém o backup do tema clássico/vintage original do Course Forge.

## Arquivos incluídos

- `base.css` - CSS do site principal
- `base.html.jinja` - Template HTML do site
- `reveal.html.jinja` - Template dos slides

## Para restaurar o tema clássico

1. Copiar o CSS:
```bash
cp themes/classic/base.css css/base.css
```

2. Copiar os templates:
```bash
cp themes/classic/base.html.jinja base.html.jinja
cp themes/classic/reveal.html.jinja reveal.html.jinja
```

3. Recompilar o site:
```bash
uv run course-forge build -c /caminho/para/vault/ -o ~/Documents/site
```
