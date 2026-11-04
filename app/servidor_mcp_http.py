"""Servidor MCP do PCP por HTTP (Streamable HTTP), para o Copilot Studio e outros clientes remotos.

Reaproveita as tools de servidor_mcp.py e acrescenta o portão de entrada:
chave no cabeçalho X-API-Key, comparada em tempo constante. Sem PCP_MCP_TOKEN, o servidor não sobe.

Execução local:  uvicorn servidor_mcp_http:app --app-dir app --port 8001
Endpoint MCP:    http://127.0.0.1:8001/mcp
"""
import os
import secrets

from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

import servidor_mcp  # noqa: F401  (registra as tools, o recurso e o prompt em servidor_mcp.mcp)

TOKEN = os.environ.get("PCP_MCP_TOKEN", "")
if len(TOKEN) < 16:
    raise SystemExit("Defina PCP_MCP_TOKEN com pelo menos 16 caracteres antes de subir o servidor.")

# O SDK recusa por padrão qualquer cabeçalho Host que não seja local (proteção contra DNS rebinding).
# Ao publicar, informe o domínio público em PCP_MCP_HOSTS (separado por vírgula), por exemplo:
#   PCP_MCP_HOSTS=abc123-8001.brs.devtunnels.ms
HOSTS = ["127.0.0.1:*", "localhost:*"] + [h.strip() for h in os.environ.get("PCP_MCP_HOSTS", "").split(",") if h.strip()]
SEGURANCA = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=HOSTS, allowed_origins=[])

# stateless_http: cada requisição é independente, sem sessão guardada no servidor (mais simples atrás de balanceador).
_mcp_app = servidor_mcp.mcp.streamable_http_app(stateless_http=True, transport_security=SEGURANCA)


async def app(scope, receive, send):
    """Portão ASGI: /saude é livre; todo o resto exige a chave."""
    if scope["type"] == "http":
        if scope["path"] == "/saude":
            await JSONResponse({"status": "ok", "servidor": "pcp-mcp"})(scope, receive, send)
            return
        cabecalhos = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        chave = cabecalhos.get("x-api-key", "")
        if not secrets.compare_digest(chave.encode(), TOKEN.encode()):
            await JSONResponse({"detail": "Chave inválida."}, status_code=401)(scope, receive, send)
            return
    await _mcp_app(scope, receive, send)