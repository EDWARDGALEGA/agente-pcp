import os
import sqlite3
import sys
import threading
from pathlib import Path

# O cliente pode iniciar este servidor de qualquer pasta: ancoramos tudo na raiz do projeto.
RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

import rag
import tools

# Importante: servidor stdio nunca escreve em stdout (é o canal do protocolo). Use stderr para logs.


class BancoPorThread:
    """O servidor executa cada tool em uma thread: cada thread usa a sua conexão somente leitura."""

    def __init__(self):
        self.local = threading.local()

    def execute(self, *args, **kwargs):
        if not hasattr(self.local, "con"):
            self.local.con = sqlite3.connect("file:data/pcp.db?mode=ro", uri=True)
        return self.local.con.execute(*args, **kwargs)


tools.db = BancoPorThread()

mcp = MCPServer(
    "pcp",
    instructions=(
        "Servidor de PCP e compras (AdventureWorks, base histórica de 2022-06 a 2025-06). "
        "Use run_sql para dados (somente SELECT) e buscar_documentos para metas, definições e políticas. "
        "O schema completo está no recurso pcp://schema."
    ),
)

SOMENTE_LEITURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)


@mcp.tool(annotations=SOMENTE_LEITURA)
def run_sql(query: str) -> str:
    """Executa um SELECT somente leitura no banco de PCP (SQLite) e devolve no máximo 20 linhas.
    Datas são texto: compare com date(coluna). Consulte o recurso pcp://schema para os nomes das tabelas e colunas."""
    return tools.run_sql(query)


@mcp.tool(annotations=SOMENTE_LEITURA)
def buscar_documentos(consulta: str) -> str:
    """Busca trechos na documentação interna (definições de KPI, metas, políticas de compras e glossário de PCP).
    Devolve até 3 trechos com a fonte no formato [arquivo > seção]. Use palavras-chave, por exemplo: meta OTD."""
    return rag.formatar(rag.buscar(consulta))


@mcp.resource("pcp://schema", mime_type="text/plain")
def schema() -> str:
    """Schema completo do banco de PCP: uma linha por tabela, com colunas e tipos."""
    linhas = []
    for tabela in tools._tabelas():
        colunas = tools.db.execute(f'PRAGMA table_info("{tabela}")').fetchall()
        linhas.append(f"{tabela}(" + ", ".join(f"{c[1]} {c[2]}" for c in colunas) + ")")
    return "\n".join(linhas)


@mcp.prompt()
def revisao_mensal(periodo: str = "2025-06") -> str:
    """Modelo de pedido para a revisão mensal de PCP de um período."""
    return (
        f"Faça a revisão mensal de PCP do período {periodo}: compare OTD, refugo e recebimento completo com as metas "
        "da documentação e identifique os 3 produtos com pior desempenho de entrega. "
        "Se o período for parcial, diga isso já no início e compare apenas janelas equivalentes."
    )


if __name__ == "__main__":
    mcp.run()