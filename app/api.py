import os
import secrets
import threading
import time
from collections import deque
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import agent
import memoria

# Falha cedo: sem token configurado, a API não sobe.
TOKEN_API = os.environ.get("PCP_API_TOKEN", "")
if not TOKEN_API:
    raise RuntimeError("Defina a variável de ambiente PCP_API_TOKEN antes de iniciar a API.")

LIMITE_POR_MINUTO = 10
ORCAMENTO_DIARIO_TOKENS = 500_000

# Um serviço não usa a memória pessoal de ninguém: isolamento, como no eval.
memoria.texto_para_prompt = lambda: ""
memoria.salvar = lambda fato: "Memória desativada neste serviço."

app = FastAPI(title="Agente de PCP", version="1.0")

_trava = threading.Lock()
_janela = deque()
_gasto = {"dia": date.today(), "tokens": 0}


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)


class Resposta(BaseModel):
    resposta: str
    tools: list[str]
    tokens: int


def autenticar(x_api_key: str = Header(default="")):
    if not secrets.compare_digest(x_api_key.encode(), TOKEN_API.encode()):
        raise HTTPException(status_code=401, detail="Chave inválida.")


def checar_limites():
    agora = time.time()
    with _trava:
        while _janela and agora - _janela[0] > 60:
            _janela.popleft()
        if len(_janela) >= LIMITE_POR_MINUTO:
            raise HTTPException(status_code=429, detail="Muitas requisições. Tente novamente em 1 minuto.")
        if _gasto["dia"] != date.today():
            _gasto.update(dia=date.today(), tokens=0)
        if _gasto["tokens"] >= ORCAMENTO_DIARIO_TOKENS:
            raise HTTPException(status_code=429, detail="Orçamento diário de tokens esgotado.")
        _janela.append(agora)


@app.get("/saude")
def saude():
    return {"status": "ok", "tokens_hoje": _gasto["tokens"], "orcamento_diario": ORCAMENTO_DIARIO_TOKENS}


@app.post("/perguntar", response_model=Resposta, dependencies=[Depends(autenticar)])
def perguntar(corpo: Pergunta):
    checar_limites()
    try:
        resposta, usadas, tokens = agent.perguntar(corpo.pergunta, [])
    except Exception as e:
        agent.registrar("erro_api", erro=str(e)[:200])
        raise HTTPException(status_code=502, detail="Falha ao consultar o modelo.")
    with _trava:
        _gasto["tokens"] += tokens
    return Resposta(resposta=resposta, tools=usadas, tokens=tokens)