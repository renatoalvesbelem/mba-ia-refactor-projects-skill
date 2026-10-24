const { ValidationError } = require('../errors');

function parseCheckoutInput(body = {}) {
    const { usr: name, eml: email, pwd: password, c_id: courseId, card } = body;

    if (!name || !email || !courseId || !card) {
        throw new ValidationError('Bad Request');
    }

    return {
        name,
        email,
        password: password || null,
        courseId: Number(courseId),
        card: String(card),
    };
}

module.exports = { parseCheckoutInput };
