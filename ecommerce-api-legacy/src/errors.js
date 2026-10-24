class AppError extends Error {
    constructor(message, statusCode = 500) {
        super(message);
        this.statusCode = statusCode;
    }
}

class ValidationError extends AppError {
    constructor(message) {
        super(message, 400);
    }
}

class NotFoundError extends AppError {
    constructor(message) {
        super(message, 404);
    }
}

class PaymentDeniedError extends AppError {
    constructor(message) {
        super(message, 400);
    }
}

class AuthError extends AppError {
    constructor(message) {
        super(message, 401);
    }
}

class ServiceUnavailableError extends AppError {
    constructor(message) {
        super(message, 503);
    }
}

module.exports = {
    AppError,
    ValidationError,
    NotFoundError,
    PaymentDeniedError,
    AuthError,
    ServiceUnavailableError,
};
