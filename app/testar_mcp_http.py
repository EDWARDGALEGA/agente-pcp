"""Testa o servidor MCP por HTTP, sem IA e sem gastar tokens.
Uso:  python app/testar_mcp_http.py [URL]      (padrão: http://127.0.0.1:8001/mcp)
A chave vem da variável PCP_MCP_TOKEN (a mesma do servidor)."""
import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"
TOKEN = os.environ.get("PCP_MCP_TOKEN", "")


def texto(resultado):
    return "".join(c.text for c in resultado.content if getattr(c, "type", "") == "text")


async def main():
    http = create_mcp_http_client(headers={"X-API-Key": TOKEN})
    async with http:
        async with streamable_http_client(URL, http_client=http) as streams:
            leitura, escrita = streams[0], streams[1]
            async with ClientSession(leitura, escrita) as sessao:
                await sessao.initialize()
                print("== TOOLS ==")
                for t in (await sessao.list_tools()).tools:
                    print(f"- {t.name}: {(t.description or '').splitlines()[0]}")
                r = await sessao.call_tool("run_sql", {"query": "SELECT COUNT(*) AS total FROM WorkOrder"})
                print("SELECT     ->", texto(r))
                r = await sessao.call_tool("run_sql", {"query": "DROP TABLE WorkOrder"})
                print("DROP TABLE ->", texto(r))
                r = await sessao.call_tool("buscar_documentos", {"consulta": "meta OTD"})
                print("DOCUMENTOS ->", texto(r)[:160].replace("\n", " "))


if __name__ == "__main__":
    asyncio.run(main())