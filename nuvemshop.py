from fastapi import APIRouter, Request
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
async def nuvemshop_callback(code: str):

    client_id = os.getenv("NUVEMSHOP_CLIENT_ID")
    client_secret = os.getenv("NUVEMSHOP_CLIENT_SECRET")

    resposta = requests.post(
        "https://www.nuvemshop.com.br/apps/authorize/token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code
        }
    )

    print("STATUS:", resposta.status_code)
    print("RESPOSTA:", resposta.text)

    return resposta.json()