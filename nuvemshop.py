from fastapi import APIRouter, Request

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