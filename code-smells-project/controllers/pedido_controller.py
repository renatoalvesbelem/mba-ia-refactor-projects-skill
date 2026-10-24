import logging

from models import pedido_model
from services import notificacao_service
from validators.pedido_validator import validar_criacao, validar_status

logger = logging.getLogger(__name__)


def criar(payload):
    usuario_id, itens = validar_criacao(payload)
    resultado = pedido_model.criar(usuario_id, itens)
    notificacao_service.notificar_pedido_criado(resultado["pedido_id"], usuario_id)
    logger.info("pedido criado id=%s usuario_id=%s", resultado["pedido_id"], usuario_id)
    return resultado


def listar_por_usuario(usuario_id):
    return pedido_model.listar_por_usuario(usuario_id)


def listar_todos():
    return pedido_model.listar_todos()


def atualizar_status(pedido_id, payload):
    payload = payload or {}
    novo_status = validar_status(payload.get("status", ""))
    pedido_model.atualizar_status(pedido_id, novo_status)
    notificacao_service.notificar_status_pedido(pedido_id, novo_status)


def relatorio_vendas():
    return pedido_model.relatorio_vendas()
