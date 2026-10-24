from middlewares.error_handler import ValidationError
from models.produto_model import CATEGORIAS_VALIDAS


def validar_produto(dados):
    if not dados:
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = str(dados["nome"])
    descricao = dados.get("descricao", "")
    categoria = dados.get("categoria", "geral")

    try:
        preco = float(dados["preco"])
        estoque = int(dados["estoque"])
    except (TypeError, ValueError):
        raise ValidationError("Preço e estoque devem ser numéricos")

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < 2:
        raise ValidationError("Nome muito curto")
    if len(nome) > 200:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }
