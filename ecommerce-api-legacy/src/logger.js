const config = require('./config');

const levels = { error: 0, warn: 1, info: 2, debug: 3 };
const currentLevel = levels[config.logLevel] ?? levels.info;

function build(level) {
    return (message, meta = {}) => {
        if (levels[level] > currentLevel) return;
        const entry = { level, message, ...meta, ts: new Date().toISOString() };
        const method = level === 'debug' ? 'log' : level;
        console[method](JSON.stringify(entry));
    };
}

module.exports = {
    error: build('error'),
    warn: build('warn'),
    info: build('info'),
    debug: build('debug'),
};
