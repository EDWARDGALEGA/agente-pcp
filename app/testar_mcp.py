import asyncio
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

RAIZ = Path(__file__).resolve().parent.parent
SERVIDOR = RAIZ / "app" / "servidor_mcp.py"


def texto(resultado):
    return "".join(c.text for c in resultado.content if getattr(c, "type", "") == "text")


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVIDOR)], cwd=str(RAIZ))
    async with stdio_client(params) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            await sessao.initialize()

            print("== TOOLS (o que o modelo pode chamar) ==")
            for t in (await sessao.list_tools()).tools:
                print(f"- {t.name}: {(t.description or '').splitlines()[0]}")
                print(f"  parâmetros: {t.input_schema.get('properties')}  somente leitura: {t.annotations.read_only_hint if t.annotations else None}")

            print("\n== RECURSOS (contexto que o app anexa) ==")
            for r in (await sessao.list_resources()).resources:
                print(f"- {r.uri}")
            schema = await sessao.read_resource("pcp://schema")
            print(schema.contents[0].text[:300], "...")

            print("\n== PROMPTS (modelos que o usuário escolhe) ==")
            for p in (await sessao.list_prompts()).prompts:
                print(f"- {p.name}")
            pedido = await sessao.get_prompt("revisao_mensal", {"periodo": "2025-05"})
            print(pedido.messages[0].content.text)

            print("\n== CHAMADAS ==")
            r = await sessao.call_tool("run_sql", {"query": "SELECT COUNT(*) AS total FROM WorkOrder"})
            print("SELECT        ->", texto(r))
            r = await sessao.call_tool("run_sql", {"query": "DROP TABLE WorkOrder"})
            print("DROP TABLE    ->", texto(r))
            r = await sessao.call_tool("run_sql", {"query": "SELECT 1; DROP TABLE WorkOrder"})
            print("DOIS COMANDOS ->", texto(r))
            r = await sessao.call_tool("buscar_documentos", {"consulta": "meta OTD"})
            print("DOCUMENTOS    ->", texto(r)[:200].replace("\n", " "))


if __name__ == "__main__":
    asyncio.run(main())