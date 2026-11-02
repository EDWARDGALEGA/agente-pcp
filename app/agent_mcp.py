import asyncio
import sys
from pathlib import Path

import anthropic
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from prompts import SYSTEM_PROMPT

# Este agente NÃO importa tools.py nem abre o banco: tudo passa pelo protocolo MCP.

RAIZ = Path(__file__).resolve().parent.parent
SERVIDOR = RAIZ / "app" / "servidor_mcp.py"
MODEL = "claude-sonnet-5-5"
MAX_STEPS = 10
MAX_TOKENS_TOTAL = 30000

client = anthropic.Anthropic()


def texto(resultado):
    return "".join(c.text for c in resultado.content if getattr(c, "type", "") == "text")


async def perguntar(sessao, system, ferramentas, pergunta):
    messages = [{"role": "user", "content": pergunta}]
    total = 0
    for passo in range(1, MAX_STEPS + 1):
        resp = await asyncio.to_thread(
            client.messages.create, model=MODEL, max_tokens=2048, system=system,
            tools=ferramentas, messages=messages,
        )
        u = resp.usage
        escrita = getattr(u, "cache_creation_input_tokens", 0) or 0
        leitura = getattr(u, "cache_read_input_tokens", 0) or 0
        print(f"[passo {passo}] tokens entrada={u.input_tokens} cache_escrita={escrita} cache_leitura={leitura} saida={u.output_tokens}")
        total += u.input_tokens + escrita + leitura + u.output_tokens
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text"), total
        resultados = []
        for b in resp.content:
            if b.type == "tool_use":
                print(f"  tool (via MCP): {b.name} {b.input}")
                r = await sessao.call_tool(b.name, b.input)
                saida = texto(r)
                if r.is_error:
                    saida = "Erro da tool: " + saida
                print("  resultado:", saida[:200])
                resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": saida})
        messages.append({"role": "user", "content": resultados})
        if total > MAX_TOKENS_TOTAL:
            return f"Parei: orçamento de tokens excedido ({total}).", total
    return "Parei: limite de passos atingido.", total


async def main():
    pergunta = " ".join(sys.argv[1:]).strip() or input("Pergunta: ").strip()
    params = StdioServerParameters(command=sys.executable, args=[str(SERVIDOR)], cwd=str(RAIZ))
    async with stdio_client(params) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            await sessao.initialize()
            # 1) O cliente DESCOBRE as tools: nada está escrito aqui sobre run_sql ou buscar_documentos.
            ferramentas = [
                {"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
                for t in (await sessao.list_tools()).tools
            ]
            print("Tools descobertas no servidor:", [f["name"] for f in ferramentas])
            # 2) O schema vem de um RECURSO do servidor, não de um import.
            schema = (await sessao.read_resource("pcp://schema")).contents[0].text
            system = [{
                "type": "text",
                "text": SYSTEM_PROMPT + "\nSchema do banco (SQLite):\n" + schema
                        + "\nNesta sessão só estão disponíveis as tools run_sql e buscar_documentos (salvar_na_memoria não está).",
                "cache_control": {"type": "ephemeral"},
            }]
            resposta, total = await perguntar(sessao, system, ferramentas, pergunta)
            print("\n" + resposta)
            print(f"\n[total de tokens: {total}]")


if __name__ == "__main__":
    asyncio.run(main())