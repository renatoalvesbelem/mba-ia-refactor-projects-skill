import logging

logger = logging.getLogger(__name__)


def notificar_pedido_criado(pedido_id, usuario_id):
    logger.info("notificacao email pedido_id=%s usuario_id=%s", pedido_id, usuario_id)
    logger.info("notificacao sms pedido_id=%s", pedido_id)
    logger.info("notificacao push pedido_id=%s", pedido_id)


def notificar_status_pedido(pedido_id, novo_status):
    if novo_status == "aprovado":
        logger.info("notificacao pedido_id=%s aprovado, preparar envio", pedido_id)
    if novo_status == "cancelado":
        logger.info("notificacao pedido_id=%s cancelado, devolver estoque", pedido_id)
