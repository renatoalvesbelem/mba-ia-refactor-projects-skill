from middlewares.error_handler import ValidationError
from models.pedido_model import STATUS_VALIDOS


def validar_criacao(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    return usuario_id, itens


def validar_status(novo_status):
    if novo_status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return novo_status
