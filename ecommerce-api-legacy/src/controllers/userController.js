const { ValidationError } = require('../errors');

function createUserController({ userModel }) {
    return {
        async remove(rawId) {
            const id = Number(rawId);
            if (!Number.isInteger(id) || id <= 0) {
                throw new ValidationError('Id de usuário inválido');
            }

            await userModel.remove(id);

            return { message: 'Usuário deletado com sucesso.' };
        },
    };
}

module.exports = { createUserController };
