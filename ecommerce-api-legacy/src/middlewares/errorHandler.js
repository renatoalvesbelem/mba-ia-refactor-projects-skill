const { AppError } = require('../errors');
const logger = require('../logger');

function errorHandler(err, req, res, next) {
    if (err instanceof AppError) {
        return res.status(err.statusCode).send(err.message);
    }

    logger.error('unhandled error', { message: err.message });
    res.status(500).json({ error: 'Erro interno' });
}

module.exports = errorHandler;
