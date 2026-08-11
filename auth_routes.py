from fastapi import APIRouter, Depends, HTTPException
from dependencies import pegar_sessao, verificar_token
from sqlalchemy.orm import Session
from main import bcrypt_context, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import datetime, timedelta, timezone
from jose import jwt
from sqlalchemy.orm import Session
from models import Usuario
from schemas import UsuarioSchema, LoginSchema


auth_router = APIRouter(prefix="/auth", tags=["auth"])


#Algumas Funções soltas

def criar_token(id_usuario, duracao_token=timedelta(days=ACCESS_TOKEN_EXPIRE_MINUTES)):
    data_expiracao = datetime.now(timezone.utc) + duracao_token
    dic_info = {"sub" : str(id_usuario), "exp" : data_expiracao}
    encoded_jwt = jwt.encode(dic_info, SECRET_KEY, ALGORITHM)
    #JWT
    #id_usuario/sub
    #data_expiração
    return encoded_jwt




def autenticar_usuario(user, senha, session):
    usuario = session.query(Usuario).filter(Usuario.user==user).first()
    if not usuario:
        return False
    elif not bcrypt_context.verify(senha, usuario.senha):
        return False
    return usuario


#ENDPOINTS

@auth_router.get("/")
async def iniciar():

    """Essa é a Primeira rota do sistema"""
    
    return {
        "massage": "first route"
    }


@auth_router.post("/criar-usuario")
async def criar_usuario(usuario_schema: UsuarioSchema, session: Session = Depends(pegar_sessao)):
    usuario = session.query(Usuario).filter_by(user=usuario_schema.user).first()
    if usuario:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    senha_criptografada = bcrypt_context.hash(usuario_schema.senha)
    novo_usuario = Usuario(usuario_schema.nome,
                           usuario_schema.user,
                          senha_criptografada,
                          usuario_schema.cargo,
                          status=True,  # Ativa o usuário por padrão
                          admin=usuario_schema.admin)
    session.add(novo_usuario)
    session.commit()
    return {
        "message": f"usuario criado com sucesso {usuario_schema.user}"
    }

@auth_router.post("/login")
async def login(login_schema: LoginSchema, session: Session = Depends(pegar_sessao)):
    usuario = autenticar_usuario(login_schema.user, login_schema.senha, session)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    access_token = criar_token(usuario.id)
    refresh_token = criar_token(usuario.id, duracao_token=timedelta(days=7))
    return {
        "access_token": access_token,
        "token_type": "Bearer"
    }

@auth_router.get("/dashboard")
async def gerar_dashboard(usuario: Usuario = Depends(verificar_token)):

    return {
        "message": "Usuario capturado com sucesso.", 
        "usuario": usuario.user,
        "id": usuario.id,
        "nome": usuario.nome
    }

@auth_router.get("/listar-user")
async def buscar_usuarios(session: Session = Depends(pegar_sessao), usuario: Usuario = Depends(verificar_token)):
    usuarios = session.query(Usuario).all()
    if not usuarios:
        raise HTTPException(status_code=404, detail="Sem usuarios criados.")
        
    return usuarios