const { AuthError, ServiceUnavailableError } = require('../errors');

function createRequireAdmin(config) {
    return function requireAdmin(req, res, next) {
        if (!config.adminToken) {
            return next(new ServiceUnavailableError('Endpoint administrativo desabilitado: configure ADMIN_TOKEN'));
        }
        if (req.get('X-Admin-Token') !== config.adminToken) {
            return next(new AuthError('Token administrativo inválido'));
        }
        next();
    };
}

module.exports = createRequireAdmin;
