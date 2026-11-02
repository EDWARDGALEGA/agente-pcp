import json
import threading
import time
from pathlib import Path

import anthropic

import memoria
import tools
from prompts import SYSTEM_PROMPT
from tools import FUNCOES, TOOLS

MODEL = "claude-sonnet-5-5"
MAX_STEPS = 10
MAX_TOKENS_TOTAL = 30000
MAX_TURNOS = 6
LOG = Path("logs/agent_log.jsonl")

client = anthropic.Anthropic()


def schema_texto(tabelas=None):
    linhas = []
    for tabela in tools._tabelas():
        if tabelas is not None and tabela not in tabelas:
            continue
        colunas = tools.db.execute(f'PRAGMA table_info("{tabela}")').fetchall()
        linhas.append(f"{tabela}(" + ", ".join(f"{c[1]} {c[2]}" for c in colunas) + ")")
    return "\n".join(linhas)


# O schema vai no prompt: o agente não precisa mais gastar chamadas descobrindo as tabelas.
SCHEMA = schema_texto()
SYSTEM_BASE = SYSTEM_PROMPT + "\nSchema do banco (SQLite):\n" + SCHEMA
TOOLS_AGENTE = [t for t in TOOLS if t["name"] not in ("list_tables", "describe_table")]


_trava_log = threading.Lock()


def registrar(evento, **dados):
    LOG.parent.mkdir(exist_ok=True)
    linha = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "evento": evento, **dados}
    with _trava_log, LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def perguntar(pergunta, historico, system_base=None, ferramentas=None, rotulo=""):
    # Sem argumentos extras, é o agente único de sempre. Com eles, vira um especialista:
    # outro prompt (system_base), outro conjunto de tools (ferramentas) e um nome (rotulo).
    ferramentas = TOOLS_AGENTE if ferramentas is None else ferramentas
    permitidas = {t["name"] for t in ferramentas}
    pref = f"[{rotulo}] " if rotulo else ""
    extra = {"agente": rotulo} if rotulo else {}
    texto_system = (system_base or SYSTEM_BASE) + memoria.texto_para_prompt()
    # cache_control marca o fim do trecho fixo (tools + system) para o cache de prompt.
    system = [{"type": "text", "text": texto_system, "cache_control": {"type": "ephemeral"}}]
    messages = list(historico) + [{"role": "user", "content": pergunta}]
    total_tokens = 0
    usadas = []
    registrar("pergunta", texto=pergunta, **extra)
    for passo in range(1, MAX_STEPS + 1):
        t0 = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=ferramentas,
            messages=messages,
        )
        ms = int((time.time() - t0) * 1000)
        entrada = resp.usage.input_tokens
        cache_escrita = getattr(resp.usage, "cache_creation_input_tokens", 0) or 0
        cache_leitura = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        saida = resp.usage.output_tokens
        print(f"{pref}[passo {passo}] tokens entrada={entrada} cache_escrita={cache_escrita} cache_leitura={cache_leitura} saida={saida} ({ms} ms)")
        total_tokens += entrada + cache_escrita + cache_leitura + saida
        registrar("llm", passo=passo, entrada=entrada, cache_escrita=cache_escrita,
                  cache_leitura=cache_leitura, saida=saida, ms=ms, total=total_tokens, **extra)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            resposta = "".join(b.text for b in resp.content if b.type == "text")
            if resp.stop_reason == "max_tokens":
                resposta += "\n\n[Resposta cortada: limite de tokens atingido]"
            registrar("resposta", total_tokens=total_tokens, parada=resp.stop_reason, **extra)
            return resposta, usadas, total_tokens
        resultados = []
        for b in resp.content:
            if b.type == "tool_use":
                usadas.append(b.name)
                print(f"  {pref}tool: {b.name} {b.input}")
                funcao = FUNCOES.get(b.name)
                if b.name not in permitidas:
                    retorno = f"Tool não permitida para este agente: {b.name}"
                elif funcao:
                    retorno = funcao(b.input)
                else:
                    retorno = f"Tool desconhecida: {b.name}"
                print(f"  {pref}resultado:", retorno[:200])
                registrar("tool", nome=b.name, args=b.input, resultado=retorno[:300], **extra)
                resultados.append(
                    {"type": "tool_result", "tool_use_id": b.id, "content": retorno}
                )
        messages.append({"role": "user", "content": resultados})
        if total_tokens > MAX_TOKENS_TOTAL:
            registrar("parada", motivo="orcamento de tokens", total=total_tokens, **extra)
            return f"Parei: orçamento de tokens excedido ({total_tokens}).", usadas, total_tokens
    return "Parei: limite de passos atingido.", usadas, total_tokens


def conversar():
    historico = []
    print("Comandos: /memoria  /esquecer N  /sair")
    while True:
        pergunta = input("\nPergunta: ").strip()
        if not pergunta:
            continue
        if pergunta == "/sair":
            break
        if pergunta == "/memoria":
            fatos = memoria.carregar()
            if not fatos:
                print("(memória vazia)")
            for f in fatos:
                print(f"  {f['id']}. {f['fato']}  [{f['data']}, {f['fonte']}]")
            continue
        if pergunta.startswith("/esquecer"):
            partes = pergunta.split()
            if len(partes) == 2 and partes[1].isdigit():
                ok = memoria.esquecer(int(partes[1]))
                print("Fato removido." if ok else "Não achei esse id.")
            else:
                print("Use: /esquecer 1")
            continue
        resposta, usadas, _ = perguntar(pergunta, historico)
        print(resposta)
        nota = ""
        if usadas:
            nota = "\n\n[registro do sistema: neste turno foram executadas as tools: " + ", ".join(usadas) + "]"
        historico += [
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": resposta + nota},
        ]
        historico = historico[-2 * MAX_TURNOS:]


if __name__ == "__main__":
    conversar()