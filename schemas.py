from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List, Text
from datetime import date

class UsuarioSchema(BaseModel):
    nome: str
    user: str
    senha: str
    cargo: str = None
    # status: Optional[bool]
    admin: Optional[bool]

    class Config:
        from_attributes = True

class LoginSchema(BaseModel):
    user: str
    senha: str

    class Config:
        from_attributes = True


class EntradaEstoqueSchema(BaseModel):
    nome_peca: str
    sku: str
    tamanho: str
    modelagem: str
    cor: str
    fornecedor_id: int
    preco_custo: Decimal
    preco_venda: Decimal
    estoque: int

    class Config:
        from_attributes = True
        
class RegistroCustoSchema(BaseModel):
    aditional_id: Optional[int] = None
    tipo: str
    descricao: Text
    quantidade: int
    valor: Decimal
    status: Optional[str] = "PENDENTE"  # 'PAGO' ou 'NAOPAGO'
    pertence: Optional[str] = "GERAL"  # 'GERAL' ou 'DROP' ou 'VENDA'
    vencimento: date
    quant_parcelas: Optional[int] = 1  # Número de parcelas, padrão é 1

    class Config:
        from_attributes = True

class ItemDropSchema(BaseModel):
    produto_id: int
    quantidade: int

    class Config:
        from_attributes = True

class ItemVendaSchema(BaseModel):
    produto_id: int
    quantidade: int

    class Config:
        from_attributes = True

class FornecedorSchema(BaseModel):
    nome: str
    cnpj: str
    telefone: str
    email: str

    class Config:
        from_attributes = True