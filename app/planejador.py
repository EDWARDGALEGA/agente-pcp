import json
import re
import time
from pathlib import Path

import agent

MAX_PASSOS = 4
MAX_TOKENS_PLANO = 120000
PASTA_RELATORIOS = Path("relatorios")

PLANEJADOR = """Você planeja análises de PCP e compras.
O analista que vai executar os passos tem acesso a um banco histórico (ordens de produção, produtos, compras e fornecedores, de 2022-06 a 2025-06) e à documentação interna (definições de KPI, metas, políticas de compras e glossário).
Dado um objetivo, quebre-o em no máximo 4 passos. Cada passo é uma pergunta autocontida, que não depende de "o passo anterior", e que o analista responde com uma ou duas consultas ou buscas.
Responda SOMENTE com JSON, neste formato: {"passos": ["pergunta 1", "pergunta 2"]}"""

REDATOR = """Você escreve relatórios executivos curtos, em português, para a gestão de PCP.
Use SOMENTE os resultados dos passos fornecidos: não invente números nem fontes.
Estrutura: 1) Resumo em 2 frases, 2) Achados (lista), 3) Recomendações (2 a 3), 4) Limitações.
Cite metas e regras no formato [arquivo > seção] quando aparecerem nos resultados.
Se algum passo falhou, diga isso nas limitações."""

CRITICO = """Você revisa relatórios com este checklist:
1. Todo número do relatório aparece nos resultados dos passos.
2. Metas e regras citam a fonte no formato [arquivo > seção].
3. O relatório responde ao objetivo.
4. Limitações e passos que falharam estão declarados (por exemplo, anos parciais).
5. Nenhuma recomendação contradiz os resultados.
6. Comparações entre períodos usam janelas equivalentes, e períodos parciais são mencionados no resumo.
Responda SOMENTE com JSON, neste formato: {"ok": true ou false, "problemas": ["..."]}"""


def chamar(system, usuario, max_tokens=2000):
    resp = agent.client.messages.create(
        model=agent.MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": usuario}],
    )
    texto = "".join(b.text for b in resp.content if b.type == "text")
    return texto, resp.usage.input_tokens + resp.usage.output_tokens


def extrair_json(texto):
    achado = re.search(r"\{.*\}", texto, re.S)
    if not achado:
        return None
    try:
        return json.loads(achado.group(0))
    except json.JSONDecodeError:
        return None


def formatar_resultados(resultados):
    blocos = []
    for i, (passo, resposta, falhou) in enumerate(resultados, 1):
        estado = " (FALHOU)" if falhou else ""
        blocos.append(f"### Passo {i}{estado}: {passo}\n{resposta[:3000]}")
    return "\n\n".join(blocos)


def rodar_plano(objetivo):
    total = 0
    agent.registrar("plano_inicio", objetivo=objetivo)

    texto, t = chamar(PLANEJADOR, f"Objetivo: {objetivo}")
    total += t
    plano = extrair_json(texto)
    passos = (plano or {}).get("passos") or []
    if not passos:
        return "Não consegui montar um plano para esse objetivo.", total
    passos = passos[:MAX_PASSOS]
    print("\nPlano:")
    for n, p in enumerate(passos, 1):
        print(f"  {n}. {p}")

    resultados = []
    replanejou = False
    i = 0
    while i < len(passos):
        if total > MAX_TOKENS_PLANO:
            print(f"\n[orçamento do plano excedido: {total} tokens]")
            agent.registrar("plano_parada", motivo="orcamento", total=total)
            break
        passo = passos[i]
        print(f"\n=== Executando passo {i + 1}/{len(passos)}: {passo}")
        resposta, _, t = agent.perguntar(passo, [])
        total += t
        falhou = resposta.startswith("Parei:")
        if falhou and not replanejou:
            replanejou = True
            print("[passo falhou: replanejando uma vez]")
            concluidos = [p for p, _, _ in resultados]
            pedido = (
                f"Objetivo: {objetivo}\n"
                f"Passos já concluídos: {json.dumps(concluidos, ensure_ascii=False)}\n"
                f"O passo '{passo}' falhou com: {resposta}\n"
                f"Proponha os passos restantes, de outro jeito, em no máximo {max(1, MAX_PASSOS - len(resultados))} passos."
            )
            texto, t = chamar(PLANEJADOR, pedido)
            total += t
            novo = (extrair_json(texto) or {}).get("passos") or []
            if novo:
                passos = passos[:i] + novo[: max(1, MAX_PASSOS - len(resultados))]
                continue
        resultados.append((passo, resposta, falhou))
        agent.registrar("plano_passo", n=i + 1, passo=passo, falhou=falhou)
        i += 1

    if not resultados:
        return "Nenhum passo foi concluído.", total

    base = f"Objetivo: {objetivo}\n\nResultados dos passos:\n{formatar_resultados(resultados)}"
    rascunho, t = chamar(REDATOR, base, max_tokens=2500)
    total += t

    texto, t = chamar(CRITICO, f"{base}\n\nRelatório a revisar:\n{rascunho}")
    total += t
    veredito = extrair_json(texto) or {"ok": True, "problemas": []}
    print("\n[crítico]", "aprovado" if veredito.get("ok") else f"problemas: {veredito.get('problemas')}")
    agent.registrar("plano_critico", ok=veredito.get("ok"), problemas=veredito.get("problemas"))

    final = rascunho
    if not veredito.get("ok"):
        problemas = "\n".join(f"- {p}" for p in veredito.get("problemas", []))
        final, t = chamar(
            REDATOR,
            f"{base}\n\nRascunho anterior:\n{rascunho}\n\nCorrija estes problemas apontados pela revisão:\n{problemas}",
            max_tokens=2500,
        )
        total += t

    agent.registrar("plano_fim", total_tokens=total)
    return final, total


if __name__ == "__main__":
    objetivo = input("Objetivo da análise: ").strip()
    relatorio, total = rodar_plano(objetivo)
    print("\n" + "=" * 60 + "\n" + relatorio)
    PASTA_RELATORIOS.mkdir(exist_ok=True)
    arquivo = PASTA_RELATORIOS / time.strftime("revisao_%Y-%m-%d_%H%M.md")
    arquivo.write_text(relatorio, encoding="utf-8")
    print(f"\n[relatório salvo em {arquivo}]")
    print(f"[total de tokens do plano: {total}]")