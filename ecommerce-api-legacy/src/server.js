const config = require('./config');
const logger = require('./logger');
const { createApp } = require('./app');
const { openDatabase, migrate, seed } = require('./models/database');
const passwordHasher = require('./services/passwordHasher');

async function main() {
    const db = await openDatabase(config.database.file);
    await migrate(db);
    await seed(db, { passwordHasher });

    const app = createApp({ db, config });
    app.listen(config.port, () => {
        logger.info(`Frankenstein LMS rodando na porta ${config.port}...`);
    });
}

main().catch((err) => {
    logger.error('falha ao iniciar aplicação', { message: err.message });
    process.exit(1);
});

module.exports = { main };
