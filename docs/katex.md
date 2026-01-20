# Usando LaTeX com KaTeX

O Course Forge utiliza o [KaTeX](https://katex.org/) para renderizar equações matemáticas de forma rápida e bonita.

## Delimitadores

Os seguintes delimitadores são suportados para escrever matemática no seu markdown:

| Tipo | Delimitadores | Descrição |
|------|---------------|-----------|
| **Display** (Bloco) | `$$ ... $$` ou `\[ ... \]` | Centralizado, em linha própria. Ideal para equações importantes. |
| **Inline** (Linha) | `$ ... $` ou `\( ... \)` | Embutido no texto. Ideal para variáveis como $x$ ou pequenas fórmulas $E=mc^2$. |

## Exemplos Básicos

### Equação em Linha
O teorema de Pitágoras é $a^2 + b^2 = c^2$.

```latex
O teorema de Pitágoras é $a^2 + b^2 = c^2$.
```

### Equação em Bloco
$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

```latex
$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$
```

---

## Equações Multilinha e Resultados em Caixas

Para derivações longas onde você deseja alinhar os sinais de igualdade e destacar o resultado final, recomendamos o ambiente `split` dentro de um bloco `$$`.

O caractere `&` é usado para definir o ponto de alinhamento (geralmente antes do sinal `=`).
Use `\\[6pt]` ou `\\[12pt]` para controlar o espaçamento vertical entre as linhas.
Use `\boxed{}` para criar uma caixa ao redor do resultado final.

### Exemplo Completo: Soma e Carry

Este exemplo mostra uma derivação passo a passo com o resultado final destacado em uma caixa, tudo mantendo o alinhamento vertical.

$$
\begin{split}
S &= \overline{A}\,\overline{B}\,C_{in}
 + \overline{A}B\overline{C_{in}}
 + A\overline{B}\overline{C_{in}}
 + ABC_{in} \\[6pt]

&= C_{in}(\overline{A}\,\overline{B} + AB)
 + \overline{C_{in}}(\overline{A}B + A\overline{B}) \\[6pt]

&= C_{in}\,\overline{(A \oplus B)}
 + \overline{C_{in}}(A \oplus B) \\[6pt]

&= A \oplus B \oplus C_{in} \\[6pt]
&\boxed{S = A \oplus B \oplus C_{in}} \\[12pt]

C_{out} &= AB\overline{C_{in}}
 + ABC_{in}
 + A\overline{B}C_{in}
 + \overline{A}BC_{in} \\[6pt]

&= AB(\overline{C_{in}} + C_{in})
 + C_{in}(A\overline{B} + \overline{A}B) \\[6pt]

&= AB + C_{in}(A \oplus B) \\[6pt]

&\boxed{C_{out} = AB + C_{in}(A \oplus B)} \\[12pt]
\end{split}
$$

**Código:**

```latex
$$
\begin{split}
S &= \overline{A}\,\overline{B}\,C_{in}
 + \overline{A}B\overline{C_{in}}
 + A\overline{B}\overline{C_{in}}
 + ABC_{in} \\[6pt]

&= C_{in}(\overline{A}\,\overline{B} + AB)
 + \overline{C_{in}}(\overline{A}B + A\overline{B}) \\[6pt]

&= C_{in}\,\overline{(A \oplus B)}
 + \overline{C_{in}}(A \oplus B) \\[6pt]

&= A \oplus B \oplus C_{in} \\[6pt]
&\boxed{S = A \oplus B \oplus C_{in}} \\[12pt]

C_{out} &= AB\overline{C_{in}}
 + ABC_{in}
 + A\overline{B}C_{in}
 + \overline{A}BC_{in} \\[6pt]

&= AB(\overline{C_{in}} + C_{in})
 + C_{in}(A\overline{B} + \overline{A}B) \\[6pt]

&= AB + C_{in}(A \oplus B) \\[6pt]

&\boxed{C_{out} = AB + C_{in}(A \oplus B)} \\[12pt]
\end{split}
$$
```

### Explicação

1.  **Ambiente `split`**: Envolvemos todo o conteúdo em `\begin{split} ... \end{split}`. Isso permite alinhar várias linhas.
2.  **Alinhamento (`&=`)**: Em cada linha, usamos `&=`. O `&` diz ao LaTeX onde alinhar. Neste caso, todos os sinais de igual ficam um embaixo do outro.
3.  **Resultado em Caixa (`&\boxed{...}`)**: Para o resultado final, também usamos `&` antes do `\boxed`. Isso faz com que a borda esquerda da caixa se alinhe verticalmente com os sinais de igual das linhas anteriores, criando uma hierarquia visual clara onde a resposta "nasce" da derivação.
4.  **Espaçamento (`\\[6pt]`)**: Adicionamos `[6pt]` (ou outro valor) após a quebra de linha `\\` para dar mais respiro entre os passos, melhorando a legibilidade.
