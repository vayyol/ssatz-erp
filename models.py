from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, func, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import declarative_base, relationship
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

db = create_engine(DATABASE_URL)

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String)
    user = Column("user", String, nullable=False)
    senha = Column("senha", String)
    cargo = Column("cargo", String)
    status = Column("status", Boolean, default=False)
    admin = Column("admin", Boolean, default=False)
    created_at = Column("created_at", DateTime, server_default=func.now())
    updated_at = Column("updated_at", DateTime, onupdate=func.now())

    def __init__(self, nome, user, senha, cargo=None, status=False, admin=False):
        self.nome = nome
        self.user = user
        self.senha = senha
        self.cargo = cargo
        self.status = status
        self.admin = admin

class Estoque(Base):
    __tablename__ = "estoque"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome_peca = Column("nome_peca", String)
    sku = Column("sku", String, unique=True)
    tamanho = Column("tamanho", String)
    modelagem = Column("modelagem", String)
    cor = Column("cor", String)
    fornecedor_id = Column("fornecedor_id", Integer, ForeignKey("fornecedores.id"))
    preco_custo = Column("preco_custo", DECIMAL(10, 2))
    preco_venda = Column("preco_venda", DECIMAL(10, 2))
    estoqueInicial = Column("estoqueInicial", Integer)
    reestoque = Column("restoque", Integer)
    vendas = Column("vendas", Integer)
    estoqueAtual = Column("estoqueAtual", Integer)
    status = Column("status", Boolean, default=True)     #NEW COLUMN
    created_at = Column("created_at", DateTime, server_default=func.now())
    updated_at = Column("updated_at", DateTime, onupdate=func.now())

    def __init__(self, nome_peca, sku, tamanho, modelagem, cor, fornecedor_id, preco_custo, preco_venda, estoqueInicial, reestoque=0, vendas=0, estoqueAtual=0, status=True):
        self.nome_peca = nome_peca
        self.sku = sku
        self.tamanho = tamanho
        self.modelagem = modelagem
        self.cor = cor
        self.fornecedor_id = fornecedor_id
        self.preco_custo = preco_custo
        self.preco_venda = preco_venda
        self.estoqueInicial = estoqueInicial
        self.reestoque = reestoque
        self.vendas = vendas
        self.estoqueAtual = estoqueAtual
        self.status = status     #NEW COLUMN


class RegistroCusto(Base):
    __tablename__ = "registro_custos"


    id = Column("id", Integer, primary_key=True, autoincrement=True)
    aditional_id = Column("aditional_id", Integer)
    usuario_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"))
    tipo = Column("tipo", String)
    descricao = Column("descricao", Text)
    quantidade = Column("quantidade", Integer)
    valor = Column("valor", DECIMAL(10, 2))
    status = Column("status", String, default="PENDENTE")  # 'PAGO' ou 'NAOPAGO'
    pertence = Column("pertence", String, default="GERAL")  # 'GERAL' ou 'DROP' ou 'VENDA'
    vencimento = Column("vencimento", DateTime)
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self,  usuario_id, tipo, descricao, quantidade, valor,pertence="GERAL", aditional_id = None, status="PENDENTE", vencimento=None):
        self.aditional_id = aditional_id
        self.usuario_id = usuario_id
        self.tipo = tipo
        self.descricao = descricao
        self.quantidade = quantidade
        self.valor = valor
        self.status = status
        self.pertence = pertence
        self.vencimento = vencimento



class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    usuario_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"))
    produto_id = Column("produto_id", Integer, ForeignKey("estoque.id"))
    tipo_movimentacao = Column("tipo_movimentacao", String)  # 'entrada' ou 'saida'
    preco_custo = Column("preco_custo", DECIMAL(10, 2))
    preco_venda = Column("preco_venda", DECIMAL(10, 2))
    quantidade = Column("quantidade", Integer)
    estoque_anterior = Column("estoque_anterior", Integer)
    estoque_depois = Column("estoque_depois", Integer)
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self, usuario_id, produto_id, tipo_movimentacao, preco_custo, preco_venda, quantidade, estoque_anterior, estoque_depois):
        self.usuario_id=usuario_id
        self.produto_id = produto_id
        self.tipo_movimentacao = tipo_movimentacao
        self.preco_custo = preco_custo
        self.preco_venda = preco_venda
        self.quantidade = quantidade
        self.estoque_anterior = estoque_anterior
        self.estoque_depois = estoque_depois

class Venda(Base):
    __tablename__ = "vendas"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    usuario_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"))
    status = Column("status", String, default="PENDENTE")
    valor_total = Column("valor_total", DECIMAL(10, 2))
    subtotal = Column("subtotal", DECIMAL(10, 2))
    valor_taxa = Column("valor_taxa", DECIMAL(10, 2))
    valor_desconto = Column("valor_desconto", DECIMAL(10, 2))
    frete = Column("frete", DECIMAL(10, 2))
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self, usuario_id, status="PENDENTE", valor_total=0.00, subtotal=0.00, valor_taxa=0.00, valor_desconto=0.00, frete=0.00):
        self.usuario_id = usuario_id
        self.status = status
        self.valor_total = valor_total
        self.subtotal = subtotal
        self.valor_taxa = valor_taxa
        self.valor_desconto = valor_desconto
        self.frete = frete    


class Drop(Base):
    __tablename__ = "drop"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    usuario_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"))
    status = Column("status", String, default="PENDENTE")
    valor_total = Column("valor_total", DECIMAL(10, 2))
    subtotal = Column("subtotal", DECIMAL(10, 2))
    created_at = Column("created_at", DateTime, server_default=func.now())
    items = relationship("ItemDrop", cascade="all, delete")

    def __init__(self, usuario_id, status="PENDENTE", valor_total=0.00, subtotal=0.00):
        self.usuario_id = usuario_id
        self.status = status
        self.valor_total = valor_total
        self.subtotal = subtotal


class ItemDrop(Base):
    __tablename__ = "item_drop"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    drop_id = Column("drop_id", Integer, ForeignKey("drop.id"))
    produto_id = Column("produto_id", Integer, ForeignKey("estoque.id"))
    quantidade = Column("quantidade", Integer)
    preco_unitario = Column("preco_unitario", DECIMAL(10, 2))
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self, drop_id, produto_id, quantidade, preco_unitario):
        self.drop_id = drop_id
        self.produto_id = produto_id
        self.quantidade = quantidade
        self.preco_unitario = preco_unitario

class ItemVenda(Base):
    __tablename__ = "item_venda"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    venda_id = Column("venda_id", Integer, ForeignKey("vendas.id"))
    produto_id = Column("produto_id", Integer, ForeignKey("estoque.id"))
    quantidade = Column("quantidade", Integer)
    preco_unitario = Column("preco_unitario", DECIMAL(10, 2))
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self, venda_id, produto_id, quantidade, preco_unitario):
        self.venda_id = venda_id
        self.produto_id = produto_id
        self.quantidade = quantidade
        self.preco_unitario = preco_unitario

class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String)
    cnpj = Column("cnpj", String)
    telefone = Column("telefone", String)
    email = Column("email", String)
    endereco = Column("endereco", String)
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self, nome, cnpj=None, telefone=None, email=None, endereco=None):
        self.nome = nome
        self.cnpj = cnpj
        self.telefone = telefone
        self.email = email
        self.endereco = endereco

class Cupons(Base):
    __tablename__ = "cupons"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    codigo = Column("codigo", String, unique=True)
    taxaDesconto = Column("taxaDesconto", DECIMAL(10, 2))
    validade = Column("validade", DateTime)
    status = Column("status", Boolean, default=True)  # True for active, False for inactive
    created_at = Column("created_at", DateTime, server_default=func.now())

    def __init__(self, codigo, taxaDesconto, validade, status=True):
        self.codigo = codigo
        self.taxaDesconto = taxaDesconto
        self.validade = validade
        self.status = status


class NuvemshopIntegracao(Base):
    __tablename__ = "nuvemshop_integracoes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String, unique=True, nullable=False, index=True)

    access_token = Column(String, nullable=False)

    scope = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )