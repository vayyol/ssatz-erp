from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from dependencies import pegar_sessao, verificar_token
from sqlalchemy.orm import Session
from models import Venda, Estoque, Usuario, MovimentacaoEstoque, RegistroCusto
from datetime import datetime, date
from zoneinfo import ZoneInfo


registration_router = APIRouter(prefix="/registrations", tags=["registrations"])


@registration_router.get("/")
async def registros():
    """
    Essa é a rota de registros do sistema. Todas vão ser gets, pq são consultas. 
    Ela retorna todas as movimentações de estoque e vendas realizadas no sistema.
    """

    return {
        "message": "Voce acessou a rota de registros"
        }  

@registration_router.get("/buscar-registros")
async def buscar_todos(session: Session = Depends(pegar_sessao)):
    movimentacoes  = session.query(RegistroCusto).all()
    if not movimentacoes:
        raise HTTPException(status_code=404, detail="Nenhuma movimentação encontrada para a data especificada.")
    
    return movimentacoes

@registration_router.get("/buscar-movimentacoes")
async def buscar_movimentacoes(session: Session = Depends(pegar_sessao)):
    movimentacoes = session.query(MovimentacaoEstoque).all()
    if not movimentacoes:
        raise HTTPException(status_code=404, detail="Nenhuma movimentação encontrada.")
    
    return movimentacoes