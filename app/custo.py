import json
from datetime import datetime
from pathlib import Path

LOG = Path("logs/agent_log.jsonl")
GAP_SEGUNDOS = 60  # mais de 1 minuto sem eventos = outra execução
ULTIMAS = 8

# Pesos relativos ao preço de 1 token de entrada (proporções típicas dos modelos Claude;
# confirme na página de preços). Servem para comparar execuções, não para faturar.
PESO_SAIDA = 5.0
PESO_CACHE_ESCRITA = 1.25
PESO_CACHE_LEITURA = 0.10


def ler_eventos():
    eventos = []
    if not LOG.exists():
        return eventos
    for linha in LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(linha)
            e["_t"] = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")
            eventos.append(e)
        except (ValueError, KeyError):
            continue
    return eventos


def agrupar(eventos):
    grupos = []
    for e in eventos:
        if not grupos or (e["_t"] - grupos[-1][-1]["_t"]).total_seconds() > GAP_SEGUNDOS:
            grupos.append([])
        grupos[-1].append(e)
    return grupos


def resumir(grupo):
    llm = [e for e in grupo if e["evento"] == "llm"]
    entrada = sum(e.get("entrada", 0) for e in llm)
    escrita = sum(e.get("cache_escrita", 0) for e in llm)
    leitura = sum(e.get("cache_leitura", 0) for e in llm)
    saida = sum(e.get("saida", 0) for e in llm)
    entrada_total = entrada + escrita + leitura
    custo = entrada + PESO_CACHE_ESCRITA * escrita + PESO_CACHE_LEITURA * leitura + PESO_SAIDA * saida
    tempos = [e["ms"] for e in llm if "ms" in e]
    return {
        "inicio": grupo[0]["ts"][5:16],
        "perguntas": sum(e["evento"] == "pergunta" for e in grupo),
        "chamadas": len(llm),
        "tools": sum(e["evento"] == "tool" for e in grupo),
        "entrada": entrada, "escrita": escrita, "leitura": leitura, "saida": saida,
        "volume": entrada_total + saida,
        "custo": custo,
        "hit": (100 * leitura / entrada_total) if entrada_total else 0,
        "ms": (sum(tempos) / len(tempos)) if tempos else None,
    }


def main():
    grupos = agrupar(ler_eventos())
    if not grupos:
        print("Log vazio. Rode o agente primeiro.")
        return
    linhas = [resumir(g) for g in grupos[-ULTIMAS:]]
    linhas = [r for r in linhas if r["chamadas"]]
    cab = f"{'início':<12}{'perg':>5}{'cham':>6}{'ch/perg':>8}{'entrada':>9}{'c.escr':>8}{'c.leit':>8}{'saída':>7}{'volume':>9}{'custo-eq':>10}{'cu/perg':>9}{'hit%':>6}{'ms/cham':>9}"
    print(cab)
    print("-" * len(cab))
    for r in linhas:
        p = max(r["perguntas"], 1)
        ms = f"{r['ms']:.0f}" if r["ms"] is not None else "n/d"
        print(f"{r['inicio']:<12}{r['perguntas']:>5}{r['chamadas']:>6}{r['chamadas'] / p:>8.1f}{r['entrada']:>9}{r['escrita']:>8}{r['leitura']:>8}"
              f"{r['saida']:>7}{r['volume']:>9}{r['custo']:>10.0f}{r['custo'] / p:>9.0f}{r['hit']:>6.0f}{ms:>9}")
    print("\ncusto-eq = entrada + 1,25 x cache_escrita + 0,10 x cache_leitura + 5 x saída (em tokens de entrada equivalentes)")


if __name__ == "__main__":
    main()