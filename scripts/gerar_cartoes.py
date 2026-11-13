"""Gera os cartões do perfil (estatísticas e linguagens) como SVG, sem depender de serviço externo.

Roda no GitHub Actions (.github/workflows/cartoes.yml) com o GITHUB_TOKEN do próprio repositório.
Se a API do GitHub falhar, o script termina com erro e os SVGs anteriores ficam como estão.
Só usa a biblioteca padrão do Python.
"""
import json, os, sys, urllib.request
from xml.sax.saxutils import escape

USUARIO = os.environ.get("USUARIO", "GeotecAMA")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cards")

# tema dracula (o mesmo do cartão antigo)
FUNDO, BORDA, TITULO, TEXTO, ICONE = "#282a36", "#44475a", "#ff6e96", "#f8f8f2", "#79dafa"
CORES = {"JavaScript": "#f1e05a", "Python": "#3572A5", "HTML": "#e34c26", "CSS": "#563d7c",
         "R": "#198CE7", "Java": "#b07219", "TypeScript": "#3178c6", "Jupyter Notebook": "#DA5B0B",
         "Shell": "#89e051", "PowerShell": "#012456", "QML": "#44a51c", "TeX": "#3D6117"}


def api(caminho):
    req = urllib.request.Request("https://api.github.com" + caminho, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "cartoes-perfil",
        **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def repos():
    todos, pag = [], 1
    while True:
        lote = api(f"/users/{USUARIO}/repos?per_page=100&type=owner&page={pag}")
        todos += lote
        if len(lote) < 100:
            return [r for r in todos if not r["fork"]]
        pag += 1


def cartao_stats(rs):
    q = lambda s: api(f"/search/issues?q={s}&per_page=1")["total_count"]
    linhas = [
        ("Repositórios públicos", len(rs)),
        ("Estrelas recebidas", sum(r["stargazers_count"] for r in rs)),
        ("Commits", api(f"/search/commits?q=author:{USUARIO}&per_page=1")["total_count"]),
        ("Pull requests", q(f"author:{USUARIO}+type:pr")),
        ("Issues", q(f"author:{USUARIO}+type:issue")),
    ]
    alt = 50 + 25 * len(linhas) + 10
    corpo = "".join(
        f'<g transform="translate(25,{70 + 25 * i})"><circle cx="5" cy="-5" r="4" fill="{ICONE}"/>'
        f'<text x="20" class="t">{escape(n)}:</text><text x="300" class="v">{f"{v:,}".replace(",", ".")}</text></g>'
        for i, (n, v) in enumerate(linhas))
    return svg(400, alt, f"Estatísticas no GitHub · {USUARIO}", corpo)


def cartao_langs(rs):
    soma = {}
    for r in rs:
        for ling, b in api(f"/repos/{USUARIO}/{r['name']}/languages").items():
            soma[ling] = soma.get(ling, 0) + b
    total = sum(soma.values()) or 1
    top = sorted(soma.items(), key=lambda x: -x[1])[:8]
    barra, x = "", 0.0
    for ling, b in top:
        w = 350 * b / total
        barra += f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="8" fill="{CORES.get(ling, "#8be9fd")}"/>'
        x += w
    itens = "".join(
        f'<g transform="translate({25 + 175 * (i % 2)},{100 + 22 * (i // 2)})">'
        f'<circle cx="5" cy="-4" r="5" fill="{CORES.get(l, "#8be9fd")}"/>'
        f'<text x="16" class="t">{escape(l)} {100 * b / total:.1f}%</text></g>'
        for i, (l, b) in enumerate(top))
    alt = 100 + 22 * ((len(top) + 1) // 2) + 5
    corpo = (f'<clipPath id="c"><rect x="0" y="0" width="350" height="8" rx="4"/></clipPath>'
             f'<g clip-path="url(#c)" transform="translate(25,65)">{barra}</g>{itens}')
    if not top:
        corpo = f'<text x="25" y="75" class="t">Sem código público ainda</text>'
    return svg(400, alt, "Linguagens mais usadas", corpo)


def svg(l, a, titulo, corpo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{l}" height="{a}" viewBox="0 0 {l} {a}" '
            f'role="img" aria-label="{escape(titulo)}"><title>{escape(titulo)}</title><style>'
            f'.h{{font:600 18px \'Segoe UI\',Ubuntu,sans-serif;fill:{TITULO}}}'
            f'.t{{font:400 14px \'Segoe UI\',Ubuntu,sans-serif;fill:{TEXTO}}}'
            f'.v{{font:700 14px \'Segoe UI\',Ubuntu,sans-serif;fill:{TEXTO};text-anchor:end}}</style>'
            f'<rect x="0.5" y="0.5" width="{l - 1}" height="{a - 1}" rx="6" fill="{FUNDO}" stroke="{BORDA}"/>'
            f'<text x="25" y="38" class="h">{escape(titulo)}</text>{corpo}</svg>\n')


if __name__ == "__main__":
    try:
        rs = repos()
        cartoes = {"stats.svg": cartao_stats(rs), "top-langs.svg": cartao_langs(rs)}
    except Exception as e:  # mantém os SVGs anteriores
        sys.exit(f"Falha na API do GitHub, cartões não alterados: {e}")
    os.makedirs(SAIDA, exist_ok=True)
    for nome, conteudo in cartoes.items():
        with open(os.path.join(SAIDA, nome), "w", encoding="utf-8") as f:
            f.write(conteudo)
        print("gerado", nome)
