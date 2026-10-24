import logging

from middlewares.error_handler import AuthError, NotFoundError
from models import usuario_model
from validators.usuario_validator import validar_criacao, validar_login

logger = logging.getLogger(__name__)


def listar():
    return usuario_model.listar_todos()


def buscar_por_id(usuario_id):
    usuario = usuario_model.buscar_por_id(usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(payload):
    dados = validar_criacao(payload)
    usuario_id = usuario_model.criar(dados["nome"], dados["email"], dados["senha"])
    logger.info("usuario criado email=%s", dados["email"])
    return usuario_id


def login(payload):
    dados = validar_login(payload)
    usuario = usuario_model.autenticar(dados["email"], dados["senha"])
    if not usuario:
        logger.info("login falhou email=%s", dados["email"])
        raise AuthError("Email ou senha inválidos")
    logger.info("login bem-sucedido email=%s", dados["email"])
    return usuario
