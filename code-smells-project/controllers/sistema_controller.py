import logging

from middlewares.auth import recusar_em_producao
from middlewares.error_handler import ValidationError
from models import sistema_model

logger = logging.getLogger(__name__)


def health_check():
    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": sistema_model.contar("produtos"),
            "usuarios": sistema_model.contar("usuarios"),
            "pedidos": sistema_model.contar("pedidos"),
        },
        "versao": "1.0.0",
    }


def resetar_banco():
    recusar_em_producao()
    sistema_model.resetar_tudo()
    logger.warning("banco de dados resetado via /admin/reset-db")


def executar_query(payload):
    payload = payload or {}
    sql = payload.get("sql", "")
    if not sql:
        raise ValidationError("Query não informada")
    if not sql.strip().upper().startswith("SELECT"):
        raise ValidationError("Somente consultas SELECT são permitidas neste endpoint")
    return sistema_model.executar_select(sql)
