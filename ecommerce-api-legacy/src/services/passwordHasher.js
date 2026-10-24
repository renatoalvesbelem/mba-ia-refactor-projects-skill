const crypto = require('node:crypto');

const KEY_LENGTH = 64;
const SALT_LENGTH = 16;

function hash(password) {
    const salt = crypto.randomBytes(SALT_LENGTH).toString('hex');
    const derivedKey = crypto.scryptSync(password, salt, KEY_LENGTH);
    return `${salt}:${derivedKey.toString('hex')}`;
}

module.exports = { hash };
