const env = process.env.NODE_ENV || 'development';
const defaultAdminToken = env === 'development' ? 'dev-admin-token-change-me' : null;

module.exports = {
    port: Number(process.env.PORT) || 3000,
    env,
    database: {
        file: process.env.DATABASE_FILE || ':memory:',
    },
    adminToken: process.env.ADMIN_TOKEN || defaultAdminToken,
    logLevel: process.env.LOG_LEVEL || 'info',
};
