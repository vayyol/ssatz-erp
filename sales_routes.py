from fastapi import APIRouter, Depends, HTTPException
from dependencies import pegar_sessao, verificar_token
from sqlalchemy.orm import Session
from models import  Estoque, Usuario, RegistroCusto, MovimentacaoEstoque, ItemVenda, Venda
from main import bcrypt_context, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES 
from schemas import EntradaEstoqueSchema, RegistroCustoSchema, ItemVendaSchema
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta

sales_router = APIRouter(prefix="/sales", tags=["sales"])

def registrar_movimentacao(session: Session, produto: Estoque, tipo_movimentacao: str, estoque_anterior: int, usuario):
    movimentacao = MovimentacaoEstoque(
            usuario_id=usuario.id,
            produto_id=produto.id,
            tipo_movimentacao=tipo_movimentacao,
            preco_custo=produto.preco_custo,
            preco_venda=produto.preco_venda,
            quantidade=estoque_anterior - produto.estoqueAtual,
            estoque_anterior=estoque_anterior,
            estoque_depois=produto.estoqueAtual
        )
    session.add(movimentacao)
    session.commit()
    return movimentacao
    

@sales_router.get("/")
async def gerenciar_vendas():
    """
    Essa é a rota de gerencia de vendas do sistema.
    """

    return {
        "message": "Voce acessou a rota de gerencia de vendas"
        }  

# so para testes, apagar deposis
@sales_router.post("/criar-vendas")
async def criar_vendas(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    new_venda = Venda(usuario_id=usuario.id)
    session.add(new_venda)
    session.commit()
    return {
            "message": "Venda criada com sucesso. ",
            "id_venda": new_venda.id
            }

@sales_router.post("/criar-venda")
async def criar_venda(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    new_venda = Venda(usuario_id=usuario.id)
    session.add(new_venda)
    session.commit()
    return {
            "message": "Venda criada com sucesso. ",
            "id_venda": new_venda.id
            }

@sales_router.post("/finalizar-venda/{id_venda}") 
async def finalizar_venda(id_venda: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    venda = session.query(Venda).filter(Venda.id==id_venda).first()
    if not venda:
        raise HTTPException(status_code=400, detail="Venda nao encontrada")
    # if usuario.id != venda.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para finalizar esse venda")
    if venda.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse venda ja foi finalizado ou cancelado")
    
    venda.status = "FINALIZADO"

    # #Registrar os custos da movimentação de estoque do tipo "venda FINALIZADO"
    registro_custo = RegistroCusto(
        aditional_id=venda.id,
        usuario_id=usuario.id,
        tipo="VENDA FINALIZADO",
        descricao=f"REGISTRANDO CUSTO PARA LOJA DO VENDA FINALIZADO DE ID {venda.id}",
        quantidade=1,
        valor=venda.valor_total,
        status="NAOPAGO",
        vencimento=datetime.now(ZoneInfo("America/Sao_Paulo")), #FAZER A MUDANÇA PARA BR DEPOIS  
    )

    #Mandando todos os status dos registros pendentes do venda para NAOPAGO
    # registros_pendentes = session.query(RegistroCusto).filter(RegistroCusto.aditional_id==venda.id).all()
    # for registro in registros_pendentes:
    #     registro.status = "NAOPAGO"
    session.add(registro_custo)

    #adicionando ao estoque os produtos do venda finalizado
    itens_venda = session.query(ItemVenda).filter(ItemVenda.venda_id==venda.id).all()
    for item in itens_venda:
        produto = session.query(Estoque).filter(Estoque.id==item.produto_id).first()
        if not produto:
            raise HTTPException(status_code=400, detail=f"Produto com id {item.produto_id} nao encontrado no estoque")
        estoque_anterior = produto.estoqueAtual
        produto.estoqueAtual -= item.quantidade
        produto.vendas += item.quantidade
        registrar_movimentacao(session, produto, "VENDA", estoque_anterior, usuario)

    session.commit()
    return {
        "message": f"venda {venda.id} finalizado com sucesso",
        "valor_total": venda.valor_total
    }


@sales_router.post("/cancelar-venda/{id_venda}")
async def cancelar_venda(id_venda: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    venda = session.query(Venda).filter(Venda.id==id_venda).first()
    if not venda:
        raise HTTPException(status_code=400, detail="Venda nao encontrada")
    # if usuario.id != venda.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para cancelar esse venda")
    if venda.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse venda ja foi finalizado ou cancelado")
    
    venda.status = "CANCELADO"

    # #apagando todos os registros de custo do venda cancelado
    # registros_custos = session.query(RegistroCusto).filter(RegistroCusto.aditional_id==venda.id).all()
    # for registro in registros_custos:
    #     session.delete(registro)

    session.commit()
    return {
        "message": f"venda {venda.id} cancelado com sucesso"
    }


@sales_router.post("/adicionar-item/{id_venda}")
async def adicionar_item_venda(id_venda: int, 
                                item_venda_schema: ItemVendaSchema, 
                                session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    venda = session.query(Venda).filter(Venda.id==id_venda).first()
    # if usuario.id != venda.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para adicionar produtos a esse venda")
    if not venda:
        raise HTTPException(status_code=400, detail="Venda nao encontrada")
    if venda.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse venda esta finalizado ou cancelado")

    produto = session.query(Estoque).filter(Estoque.id==item_venda_schema.produto_id).first()
    if not produto:
        raise HTTPException(status_code=400, detail="Nao existe produto no estoque com esse id")
    # produto.estoque += item_venda_schema.quantidade

    item_venda = ItemVenda(venda.id, item_venda_schema.produto_id, item_venda_schema.quantidade, produto.preco_venda)
    venda.subtotal += item_venda.quantidade * produto.preco_venda
    venda.valor_total += venda.subtotal 
    session.add(item_venda)
    session.commit()
    return {
        "message": f"Item adicionado ao pedido {venda.id} com sucesso",
        "item_id": item_venda.id, 
        "preco_pedido": venda.valor_total
    }

@sales_router.post("/remover-item/{id_item_venda}")
async def remover_item_venda(id_item_venda: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    item_venda = session.query(ItemVenda).filter(ItemVenda.id==id_item_venda).first()
    if not item_venda:
        raise HTTPException(status_code=400, detail="Item do venda nao encontrado")
    
    venda = session.query(Venda).filter(Venda.id==item_venda.venda_id).first()
    # if usuario.id != venda.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para remover produtos desse venda")
    if not venda:
        raise HTTPException(status_code=400, detail="Venda nao encontrada")
    if venda.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse venda esta finalizado ou cancelado")

    produto = session.query(Estoque).filter(Estoque.id==item_venda.produto_id).first()
    venda.subtotal -= item_venda.quantidade * produto.preco_venda
    venda.valor_total -= item_venda.quantidade * produto.preco_venda
    # produto.estoque -= item_venda.quantidade
    session.delete(item_venda)
    session.commit()
    return {
        "message": f"Item removido do pedido {venda.id} com sucesso",
        "preco_pedido": venda.valor_total
    }


@sales_router.post("/registrar-custo")
async def registrar_custo(schema: RegistroCustoSchema, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    valor_parcela = schema.valor / schema.quant_parcelas
    for i in range(schema.quant_parcelas):
        registro = RegistroCusto(
            aditional_id=schema.aditional_id,
            usuario_id=usuario.id,
            tipo=schema.tipo,
            descricao=schema.descricao,
            quantidade=schema.quantidade,
            valor=valor_parcela,
            status=schema.status,
            vencimento=schema.vencimento + relativedelta(months=i),
        )

        session.add(registro)

    session.commit()
    return {
        "message": f"Registro de custo '{schema.tipo}' criado com sucesso."
        }



# @sales_router.post("/registrar-custo-auto")
# async def registrar_custo(schema: RegistroCustoSchema, session: Session = Depends(pegar_sessao)):
#     valor_parcela = schema.valor / schema.quant_parcelas
#     for i in range(schema.quant_parcelas):
#         registro = RegistroCusto(
#             aditional_id=schema.aditional_id,
#             usuario_id=1,
#             tipo=schema.tipo,
#             descricao=schema.descricao,
#             quantidade=schema.quantidade,
#             valor=valor_parcela,
#             pertence=schema.pertence,
#             vencimento=schema.vencimento + relativedelta(months=i),
#         )

#     venda = session.query(Venda).filter(Venda.id==schema.aditional_id).first()
#     if not venda:
#         raise HTTPException(status_code=400, detail="Venda nao encontrada")
#     if venda.status != "PENDENTE":
#         raise HTTPException(status_code=401, detail="essa venda esta finalizado ou cancelado")

#     session.add(registro)
#     venda.valor_total += registro.valor

#     session.commit()
#     return {
#         "message": f"Registro de custo '{schema.tipo}' criado com sucesso."
#         }


@sales_router.delete("/apagar-custo/{id_registro}")
async def apagar_custo(id_registro: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    registro = session.query(RegistroCusto).filter(RegistroCusto.id == id_registro).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro de custo não encontrado.")
    if registro.pertence == "venda":
        venda = session.query(Venda).filter(Venda.id == registro.aditional_id).first()
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada.")
        venda.valor_total -= registro.valor

    session.delete(registro)
    session.commit()
    return {
        "message": f"Registro de custo '{registro.tipo}' apagado com sucesso."
    }


@sales_router.get("/buscar-vendas")
async def buscar_vendas(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    vendas = session.query(Venda).all()
    if not vendas:
        raise HTTPException(status_code=404, detail="Nenhuma venda foi iniciada.")

    return vendas

@sales_router.get("/buscar-venda/{id_venda}")
async def buscarvenda(id_venda: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    venda = session.query(Venda).filter(Venda.id == id_venda).first()
    if not venda:
        raise HTTPException(status_code=404, detail="Nenhuma venda foi encontrada com esse id.")
    return venda

@sales_router.get("/buscar-itens/{id_venda}")
async def buscarItens(id_venda: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    itens = session.query(ItemVenda).filter(ItemVenda.venda_id == id_venda).all()
    if not itens:
        raise HTTPException(status_code=404, detail="Nenhum produto foi adicionado a essa venda.")
    return itens
