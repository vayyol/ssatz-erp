from fastapi import APIRouter, Depends, HTTPException
from dependencies import pegar_sessao, verificar_token
from sqlalchemy.orm import Session
from models import  Estoque, Usuario, RegistroCusto, MovimentacaoEstoque, Drop, ItemDrop, Venda, ItemVenda, Fornecedor
from main import bcrypt_context, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES 
from schemas import EntradaEstoqueSchema, RegistroCustoSchema, ItemDropSchema, FornecedorSchema
from typing import Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta

order_router = APIRouter(prefix="/order", tags=["order"])

agora = datetime.now(ZoneInfo("America/Sao_Paulo"))

def registrar_movimentacao(session: Session, produto: Estoque, tipo_movimentacao: str, estoque_anterior: int, usuario):
    movimentacao = MovimentacaoEstoque(
            usuario_id=usuario.id,
            produto_id=produto.id,
            tipo_movimentacao=tipo_movimentacao,
            preco_custo=produto.preco_custo,
            preco_venda=produto.preco_venda,
            quantidade=produto.estoqueAtual-estoque_anterior,
            estoque_anterior=estoque_anterior,
            estoque_depois=produto.estoqueAtual
        )
    session.add(movimentacao)
    session.commit()
    return movimentacao
    

@order_router.get("/")
async def gerenciar_estoque():
    """
    Essa é a rota de gerencia de estoque do sistema.
    """

    return {
        "message": "Voce acessou a rota de gerencia de estoque"
        }  



@order_router.post("/entrada-estoque")
async def entrada_estoque(schema: EntradaEstoqueSchema, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    #verificar se já existe um produto com o mesmo nome ou código de barras no estoque
    produto_codigo = session.query(Estoque).filter(Estoque.sku == schema.sku).first()
    if produto_codigo:
        raise HTTPException(status_code=404, detail="Já existe um produto com esse código de barras no estoque.")
    
    #Criar o produto no estoque
    novo_produto = Estoque(schema.nome_peca, schema.sku, schema.tamanho, 
                           schema.modelagem, schema.cor, schema.fornecedor_id, schema.preco_custo, 
                           schema.preco_venda, schema.estoque, 0, 0, schema.estoque)
    session.add(novo_produto)

    session.commit()

    #Registrar os custos da movimentação de estoque do tipo "DROP FINALIZADO"
    registro_custo = RegistroCusto(
        aditional_id=novo_produto.id,
        usuario_id=usuario.id,
        tipo="CRIAÇÃO",
        descricao=f"REGISTRANDO CUSTO PARA LOJA DE CROAÇÃO DE ID {novo_produto.id}",
        quantidade=1,
        valor=novo_produto.preco_custo * novo_produto.estoqueAtual,
        status="NAOPAGO",
        vencimento=datetime.now(ZoneInfo("America/Sao_Paulo")), #FAZER A MUDANÇA PARA BR DEPOIS  
    )

    session.add(registro_custo)
    
    #Registrar a movimentação de estoque do tipo "CRIACAO"
    session.commit()  # Commit para garantir que o produto seja criado e tenha um ID
    produto_criado = session.query(Estoque).filter(Estoque.sku == schema.sku).first()
    estoque_anterior = 0  # Como é uma entrada de estoque, o estoque anterior é 0
    registrar_movimentacao(session, produto_criado, "CRIACAO", estoque_anterior, usuario)
    session.commit()

    return {
        "message": f"Produto '{schema.nome_peca}' adicionado ao estoque com sucesso."}


# so para testes, apagar deposis
@order_router.post("/criar-drops")
async def criar_drop(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    new_drop = Drop(usuario_id=usuario.id)
    session.add(new_drop)
    session.commit()
    return {
            "message": "Drop criado com sucesso. ",
            "id_drop": new_drop.id
            }

@order_router.post("/criar-drop")
async def criar_drop(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    new_drop = Drop(usuario_id=usuario.id)
    session.add(new_drop)
    session.commit()
    return {
            "message": "Drop criado com sucesso. ",
            "id_drop": new_drop.id
            }

@order_router.post("/finalizar-drop/{id_drop}") 
async def finalizar_drop(id_drop: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    drop = session.query(Drop).filter(Drop.id==id_drop).first()
    if not drop:
        raise HTTPException(status_code=400, detail="Drop nao encontrado")
    # if usuario.id != drop.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para finalizar esse drop")
    if drop.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse drop ja foi finalizado ou cancelado")
    
    drop.status = "FINALIZADO"

    #Registrar os custos da movimentação de estoque do tipo "DROP FINALIZADO"
    registro_custo = RegistroCusto(
        aditional_id=drop.id,
        usuario_id=usuario.id,
        tipo="REESTOQUE",
        descricao=f"REGISTRANDO CUSTO PARA REESTOQUE DE ID {drop.id}",
        quantidade=1,
        valor=drop.valor_total,
        status="NAOPAGO",
        vencimento=datetime.now(ZoneInfo("America/Sao_Paulo")), #FAZER A MUDANÇA PARA BR DEPOIS  
    )

    #Mandando todos os status dos registros pendentes do drop para NAOPAGO
    # registros_pendentes = session.query(RegistroCusto).filter(RegistroCusto.aditional_id==drop.id).all()
    # for registro in registros_pendentes:
    #     registro.status = "NAOPAGO"
    session.add(registro_custo)

    #adicionando ao estoque os produtos do drop finalizado
    itens_drop = session.query(ItemDrop).filter(ItemDrop.drop_id==drop.id).all()
    for item in itens_drop:
        produto = session.query(Estoque).filter(Estoque.id==item.produto_id).first()
        if not produto:
            raise HTTPException(status_code=400, detail=f"Produto com id {item.produto_id} nao encontrado no estoque")
        estoque_anterior = produto.estoqueAtual
        if produto.estoqueAtual is None:
            produto.estoqueAtual = 0
        produto.estoqueAtual += item.quantidade
        produto.reestoque += item.quantidade
        registrar_movimentacao(session, produto, "REESTOQUE", estoque_anterior, usuario)

    session.commit()
    return {
        "message": f"Reestoque {drop.id} finalizado com sucesso",
        "valor_total": drop.valor_total
    }


@order_router.post("/cancelar-drop/{id_drop}")
async def cancelar_drop(id_drop: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    drop = session.query(Drop).filter(Drop.id==id_drop).first()
    if not drop:
        raise HTTPException(status_code=400, detail="Drop nao encontrado")
    # if usuario.id != drop.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para cancelar esse drop")
    if drop.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse drop ja foi finalizado ou cancelado")
    
    drop.status = "CANCELADO"

    # #apagando todos os registros de custo do drop cancelado
    # registros_custos = session.query(RegistroCusto).filter(RegistroCusto.aditional_id==drop.id).all()
    # for registro in registros_custos:
    #     session.delete(registro)

    session.commit()
    return {
        "message": f"Drop {drop.id} cancelado com sucesso"
    }


@order_router.post("/adicionar-item/{id_drop}")
async def adicionar_item_drop(id_drop: int, 
                                item_drop_schema: ItemDropSchema, 
                                session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    drop = session.query(Drop).filter(Drop.id==id_drop).first()
    # if usuario.id != drop.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para adicionar produtos a esse drop")
    if not drop:
        raise HTTPException(status_code=400, detail="Drop nao encontrado")
    if drop.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse drop esta finalizado ou cancelado")

    produto = session.query(Estoque).filter(Estoque.id==item_drop_schema.produto_id).first()
    if not produto:
        raise HTTPException(status_code=400, detail="Nao existe produto no estoque com esse id")
    # produto.estoque += item_drop_schema.quantidade

    item_drop = ItemDrop(drop.id, item_drop_schema.produto_id, item_drop_schema.quantidade, produto.preco_custo)
    drop.subtotal += item_drop.quantidade * produto.preco_custo
    drop.valor_total = drop.subtotal 
    session.add(item_drop)
    session.commit()
    return {
        "message": f"Item adicionado ao pedido {drop.id} com sucesso",
        "item_id": item_drop.id, 
        "preco_pedido": drop.valor_total
    }

@order_router.post("/remover-item/{id_item_drop}")
async def remover_item_drop(id_item_drop: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    item_drop = session.query(ItemDrop).filter(ItemDrop.id==id_item_drop).first()
    if not item_drop:
        raise HTTPException(status_code=400, detail="Item do drop nao encontrado")
    
    drop = session.query(Drop).filter(Drop.id==item_drop.drop_id).first()
    # if usuario.id != drop.usuario_id:
    #     raise HTTPException(status_code=401, detail="sem autorizacao para remover produtos desse drop")
    if not drop:
        raise HTTPException(status_code=400, detail="Drop nao encontrada")
    if drop.status != "PENDENTE":
        raise HTTPException(status_code=401, detail="esse drop esta finalizado ou cancelado")

    produto = session.query(Estoque).filter(Estoque.id==item_drop.produto_id).first()
    drop.subtotal -= item_drop.quantidade * produto.preco_custo
    drop.valor_total -= item_drop.quantidade * produto.preco_custo
    # produto.estoque -= item_drop.quantidade
    session.delete(item_drop)
    session.commit()
    return {
        "message": f"Item removido do pedido {drop.id} com sucesso",
        "preco_pedido": drop.valor_total
    }


@order_router.post("/registrar-custo")
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



# @order_router.post("/registrar-custo-auto")
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

#     drop = session.query(Drop).filter(Drop.id==schema.aditional_id).first()
#     if not drop:
#         raise HTTPException(status_code=400, detail="Drop nao encontrada")
#     if drop.status != "PENDENTE":
#         raise HTTPException(status_code=401, detail="esse drop esta finalizado ou cancelado")

#     session.add(registro)
#     drop.valor_total += registro.valor

#     session.commit()
#     return {
#         "message": f"Registro de custo '{schema.tipo}' criado com sucesso."
#         }


@order_router.delete("/apagar-custo/{id_registro}")
async def apagar_custo(id_registro: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    registro = session.query(RegistroCusto).filter(RegistroCusto.id == id_registro).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro de custo não encontrado.")
    if registro.pertence == "DROP":
        drop = session.query(Drop).filter(Drop.id == registro.aditional_id).first()
        if not drop:
            raise HTTPException(status_code=404, detail="Drop não encontrada.")
        drop.valor_total -= registro.valor

    session.delete(registro)
    session.commit()
    return {
        "message": f"Registro de custo '{registro.tipo}' apagado com sucesso."
    }


@order_router.get("/buscar-drops")
async def buscar_drops(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    drops = session.query(Drop).all()
    if not drops:
        raise HTTPException(status_code=404, detail="SNenhuma drop foi iniciada.")

    return drops

@order_router.get("/buscar-drop/{id_drop}")
async def buscardrop(id_drop: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    drop = session.query(Drop).filter(Drop.id == id_drop).first()
    if not drop:
        raise HTTPException(status_code=404, detail="Nenhuma drop foi encontrada com esse id.")
    return drop

@order_router.get("/buscar-itens/{id_drop}")
async def buscarItens(id_drop: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    itens = session.query(ItemDrop).filter(ItemDrop.drop_id == id_drop).all()
    if not itens:
        raise HTTPException(status_code=404, detail="Nenhum produto foi adicionado a essa drop.")
    return itens




@order_router.post("/desativar-estoque/{id_produto}")
async def desativar_estoque(id_produto: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    produto = session.query(Estoque).filter(Estoque.id == id_produto).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado no estoque.")
    if produto.status == False:
        raise HTTPException(status_code=400, detail="Produto já está inativo no estoque.")
    produto.status = False
    session.commit()
    registrar_movimentacao(session, produto, "DESATIVACAO", produto.estoqueAtual, usuario)

    return {
        "message": f"Produto '{produto.nome_peca}' desativado com sucesso."
    }
    
    
@order_router.post("/reativar-estoque/{id_produto}")
async def reativar_estoque(id_produto: int, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    produto = session.query(Estoque).filter(Estoque.id == id_produto).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado no estoque.")
    if produto.status == True:
        raise HTTPException(status_code=400, detail="Produto já está ativo no estoque.")
    produto.status = True
    session.commit()
    registrar_movimentacao(session, produto, "REATIVACAO", produto.estoqueAtual, usuario)

    return {
        "message": f"Produto '{produto.nome_peca}' reativado com sucesso."
    }

@order_router.get("/buscar")
async def buscar_estoque(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):

    produtos = session.query(Estoque).all()
    if not produtos:
        raise HTTPException(status_code=404, detail="Sem produtos no estoque.")
    
    return produtos


@order_router.get("/excuir_tudo")
async def excluir_tudo(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    session.query(MovimentacaoEstoque).delete()
    session.query(RegistroCusto).delete()
    session.query(ItemDrop).delete()
    session.query(Drop).delete()
    session.query(ItemVenda).delete()
    session.query(Venda).delete()
    session.query(Estoque).delete()
    session.commit()
    return {"message": "Todos os registros foram excluídos com sucesso."}

@order_router.post("/criar-fornecedor")
async def criar_fornecedor(schema: FornecedorSchema, session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    fornecedor = Fornecedor(
        nome=schema.nome,
        cnpj=schema.cnpj,
        telefone=schema.telefone,
        email=schema.email, 
        endereco="",  # Adicione o campo de endereço se necessário
    )
    session.add(fornecedor)
    session.commit()
    return {"message": f"Fornecedor '{schema.nome}' criado com sucesso."}

@order_router.get("/listar-fornecedores")
async def listar_fornecedores(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    fornecedores = session.query(Fornecedor).all()
    if not fornecedores:
        raise HTTPException(status_code=404, detail="Nenhum fornecedor encontrado.")

    return fornecedores