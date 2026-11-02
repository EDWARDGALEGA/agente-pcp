import sqlite3
import threading

import memoria
import rag


class BancoPorThread:
    """Cada thread usa a sua própria conexão somente leitura (necessário para equipe, MCP e API)."""

    def __init__(self):
        self.local = threading.local()

    def execute(self, *args, **kwargs):
        if not hasattr(self.local, "con"):
            self.local.con = sqlite3.connect("file:data/pcp.db?mode=ro", uri=True)
        return self.local.con.execute(*args, **kwargs)


db = BancoPorThread()

MAX_LINHAS = 20
MAX_CHARS = 4000

TOOLS = [
    {
        "name": "list_tables",
        "description": "Lista as tabelas do banco. Use antes de escrever SQL.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "describe_table",
        "description": "Mostra colunas, tipos e 3 linhas de exemplo de uma tabela.",
        "input_schema": {
            "type": "object",
            "properties": {"table": {"type": "string", "description": "Nome da tabela"}},
            "required": ["table"],
        },
    },
    {
        "name": "run_sql",
        "description": "Executa um SELECT somente leitura (SQLite). Devolve no máximo 20 linhas.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta SELECT"}},
            "required": ["query"],
        },
    },
    {
        "name": "salvar_na_memoria",
        "description": "Guarda um fato durável do usuário (preferência, definição de negócio ou lição aprendida) para sessões futuras. Use só quando o usuário pedir para lembrar algo. Nunca guarde senhas, chaves ou dados pessoais. O usuário confirma antes de salvar.",
        "input_schema": {
            "type": "object",
            "properties": {"fato": {"type": "string", "description": "O fato, em uma frase curta"}},
            "required": ["fato"],
        },
    },
    {
        "name": "buscar_documentos",
        "description": "Busca trechos na documentação interna (definições de KPI, metas, políticas de compras, glossário de PCP). Devolve até 3 trechos com a fonte. Use para perguntas sobre definições, metas, regras e procedimentos.",
        "input_schema": {
            "type": "object",
            "properties": {"consulta": {"type": "string", "description": "Palavras-chave da busca, por exemplo: meta OTD"}},
            "required": ["consulta"],
        },
    },
]


def _tabelas():
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [r[0] for r in rows]


def list_tables():
    return ", ".join(_tabelas())


def describe_table(table):
    if table not in _tabelas():
        return f"Tabela '{table}' não existe. Use list_tables."
    cols = db.execute(f'PRAGMA table_info("{table}")').fetchall()
    colunas = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
    exemplo = db.execute(f'SELECT * FROM "{table}" LIMIT 3').fetchall()
    return f"Colunas: {colunas}\nExemplo: {exemplo}"[:MAX_CHARS]


def run_sql(query):
    q = query.strip().lower()
    if not (q.startswith("select") or q.startswith("with")):
        return "Bloqueado: só é permitido SELECT."
    try:
        linhas = db.execute(query).fetchmany(MAX_LINHAS)
        return str(linhas)[:MAX_CHARS]
    except Exception as e:
        return f"SQL error: {e}"


FUNCOES = {
    "list_tables": lambda args: list_tables(),
    "describe_table": lambda args: describe_table(args["table"]),
    "run_sql": lambda args: run_sql(args["query"]),
    "salvar_na_memoria": lambda args: memoria.salvar(args["fato"]),
    "buscar_documentos": lambda args: rag.formatar(rag.buscar(args["consulta"])),
}