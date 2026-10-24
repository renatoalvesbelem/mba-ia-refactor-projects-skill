from marshmallow import ValidationError as MarshmallowValidationError

from middlewares.error_handler import ValidationError


def load_or_raise(schema, payload):
    if not payload:
        raise ValidationError("Dados inválidos")
    try:
        return schema.load(payload)
    except MarshmallowValidationError as err:
        raise ValidationError(_first_message(err.messages) or "Dados inválidos")


def _first_message(messages):
    if isinstance(messages, dict):
        for value in messages.values():
            result = _first_message(value)
            if result:
                return result
    elif isinstance(messages, list):
        for item in messages:
            result = _first_message(item)
            if result:
                return result
    elif isinstance(messages, str):
        return messages
    return None
