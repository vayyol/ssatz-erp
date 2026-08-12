from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from models import NuvemshopIntegracao
from dependencies import pegar_sessao
import os
import requests

nuvem_router = APIRouter(prefix="/nuvemshop", tags=["Nuvemshop"])


@nuvem_router.post("/webhooks/store-redact")
async def store_redact(request: Request):
    data = await request.json()

    print("STORE REDACT:", data)

    return {"status": "ok"}


@nuvem_router.post("/webhooks/customers-redact")
async def customers_redact(request: Request):
    data = await request.json()

    print("CUSTOMERS REDACT:", data)

    return {"status": "ok"}


@nuvem_router.post("/webhooks/customers-data-request")
async def customers_data_request(request: Request):
    data = await request.json()

    print("CUSTOMERS DATA REQUEST:", data)

    return {"status": "ok"}


@nuvem_router.get("/callback")
async def nuvemshop_callback(
    code: str,
    session: Session = Depends(pegar_sessao)
):

    client_id = os.getenv("NUVEMSHOP_CLIENT_ID")
    client_secret = os.getenv("NUVEMSHOP_CLIENT_SECRET")

    resposta = requests.post(
        "https://www.nuvemshop.com.br/apps/authorize/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code
        }
    )

    if resposta.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao autenticar Nuvemshop: {resposta.text}"
        )

    dados = resposta.json()

    access_token = dados["access_token"]
    user_id = str(dados["user_id"])
    scope = dados.get("scope")

    integracao = (
        session.query(NuvemshopIntegracao)
        .filter(NuvemshopIntegracao.user_id == user_id)
        .first()
    )

    if integracao:

        integracao.access_token = access_token
        integracao.scope = scope

    else:

        integracao = NuvemshopIntegracao(
            user_id=user_id,
            access_token=access_token,
            scope=scope
        )

        session.add(integracao)

    session.commit()

    return {
        "status": "Nuvemshop conectada",
        "user_id": user_id
    }


@nuvem_router.get("/pedidos")
async def buscar_pedidos(
    session: Session = Depends(pegar_sessao)
):

    integracao = (
        session.query(NuvemshopIntegracao)
        .order_by(NuvemshopIntegracao.id.desc())
        .first()
    )

    if not integracao:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma loja Nuvemshop conectada"
        )

    resposta = requests.get(
        "https://api.nuvemshop.com.br/v1/"
        f"{integracao.user_id}/orders",
        headers={
            "Authentication": f"bearer {integracao.access_token}",
            "User-Agent": "SSATZ ERP (guiih98098@email.com)"
        }
    )

    if resposta.status_code != 200:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return resposta.json()