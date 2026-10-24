import logging

from middlewares.error_handler import NotFoundError, ValidationError
from models import produto_model
from validators.produto_validator import validar_produto

logger = logging.getLogger(__name__)


def listar():
    return produto_model.listar_todos()


def buscar_por_id(produto_id):
    produto = produto_model.buscar_por_id(produto_id)
    if not produto:
        raise NotFoundError("Produto não encontrado")
    return produto


def criar(payload):
    dados = validar_produto(payload)
    produto_id = produto_model.criar(**dados)
    logger.info("produto criado id=%s", produto_id)
    return produto_id


def atualizar(produto_id, payload):
    if not produto_model.buscar_por_id(produto_id):
        raise NotFoundError("Produto não encontrado")
    dados = validar_produto(payload)
    produto_model.atualizar(produto_id, **dados)


def deletar(produto_id):
    if not produto_model.buscar_por_id(produto_id):
        raise NotFoundError("Produto não encontrado")
    produto_model.deletar(produto_id)
    logger.info("produto deletado id=%s", produto_id)


def buscar(termo, categoria, preco_min_raw, preco_max_raw):
    try:
        preco_min = float(preco_min_raw) if preco_min_raw else None
        preco_max = float(preco_max_raw) if preco_max_raw else None
    except ValueError:
        raise ValidationError("preco_min e preco_max devem ser numéricos")

    return produto_model.buscar(termo, categoria, preco_min, preco_max)
