
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

PASTA = Path("docs")
MAX_CHUNK = 900
MAX_CHARS = 4000
K1 = 1.5
B = 0.75
STOP = {
    "de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "em", "no", "na", "nos",
    "nas", "um", "uma", "para", "por", "com", "que", "qual", "quais", "como", "se", "ao",
    "ou", "foi", "ser", "sao", "tem", "mais", "mas",
}

_cache = {"assinatura": None, "chunks": [], "df": Counter(), "avgdl": 0.0}


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _tokens(texto):
    palavras = re.findall(r"[a-z0-9]+", _normalizar(texto))
    return [p[:4] if len(p) > 4 else p for p in palavras if p not in STOP and len(p) > 1]


def _dividir(corpo):
    partes, atual = [], ""
    for par in corpo.split("\n\n"):
        if atual and len(atual) + len(par) > MAX_CHUNK:
            partes.append(atual.strip())
            atual = ""
        atual += par + "\n\n"
    if atual.strip():
        partes.append(atual.strip())
    return partes


def _chunks_do_arquivo(caminho):
    secao, linhas, chunks = "inicio", [], []
    for linha in caminho.read_text(encoding="utf-8").splitlines() + ["# fim"]:
        if linha.startswith("#"):
            corpo = "\n".join(linhas).strip()
            if corpo:
                for parte in _dividir(corpo):
                    chunks.append({"fonte": caminho.name, "secao": secao, "texto": parte})
            secao, linhas = linha.lstrip("#").strip(), []
        else:
            linhas.append(linha)
    return chunks


def _indice():
    arquivos = sorted(PASTA.glob("*.md"))
    assinatura = tuple((a.name, a.stat().st_mtime) for a in arquivos)
    if assinatura != _cache["assinatura"]:
        chunks = []
        for a in arquivos:
            chunks += _chunks_do_arquivo(a)
        df = Counter()
        for c in chunks:
            c["tokens"] = Counter(_tokens(c["secao"] + " " + c["texto"]))
            c["len"] = sum(c["tokens"].values())
            df.update(c["tokens"].keys())
        avgdl = sum(c["len"] for c in chunks) / len(chunks) if chunks else 0.0
        _cache.update(assinatura=assinatura, chunks=chunks, df=df, avgdl=avgdl)
    return _cache


def buscar(consulta, k=3):
    idx = _indice()
    n = len(idx["chunks"])
    termos = set(_tokens(consulta))
    resultados = []
    for c in idx["chunks"]:
        score = 0.0
        for t in termos:
            f = c["tokens"].get(t, 0)
            if f == 0:
                continue
            df = idx["df"][t]
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * c["len"] / idx["avgdl"]))
        if score > 0:
            resultados.append((score, c))
    resultados.sort(key=lambda x: x[0], reverse=True)
    return resultados[:k]


def formatar(resultados):
    if not resultados:
        return "Nenhum trecho relevante encontrado na documentação."
    partes = [
        f"[fonte: {c['fonte']} > {c['secao']}] (relevância {score:.2f})\n{c['texto']}"
        for score, c in resultados
    ]
    return "\n\n---\n\n".join(partes)[:MAX_CHARS]