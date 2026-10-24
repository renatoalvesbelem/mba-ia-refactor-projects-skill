const sqlite3 = require('sqlite3').verbose();

function promisify(rawDb) {
    return {
        raw: rawDb,
        run(sql, params = []) {
            return new Promise((resolve, reject) => {
                rawDb.run(sql, params, function callback(err) {
                    if (err) return reject(err);
                    resolve({ lastID: this.lastID, changes: this.changes });
                });
            });
        },
        get(sql, params = []) {
            return new Promise((resolve, reject) => {
                rawDb.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
            });
        },
        all(sql, params = []) {
            return new Promise((resolve, reject) => {
                rawDb.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
            });
        },
        exec(sql) {
            return new Promise((resolve, reject) => {
                rawDb.exec(sql, (err) => (err ? reject(err) : resolve()));
            });
        },
    };
}

function openDatabase(file) {
    return new Promise((resolve, reject) => {
        const rawDb = new sqlite3.Database(file, (err) => {
            if (err) return reject(err);
            resolve(promisify(rawDb));
        });
    });
}

async function migrate(db) {
    await db.run('PRAGMA foreign_keys = ON');
    await db.exec(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            pass TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            course_id INTEGER NOT NULL REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT (datetime('now'))
        );
    `);
}

async function seed(db, { passwordHasher }) {
    const existingUser = await db.get('SELECT id FROM users WHERE email = ?', ['leonan@fullcycle.com.br']);
    if (existingUser) return;

    const passwordHash = passwordHasher.hash('123');
    const { lastID: userId } = await db.run(
        'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        ['Leonan', 'leonan@fullcycle.com.br', passwordHash],
    );
    const { lastID: cleanArchitectureId } = await db.run(
        'INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
        ['Clean Architecture', 997.0],
    );
    await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', ['Docker', 497.0]);
    const { lastID: enrollmentId } = await db.run(
        'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
        [userId, cleanArchitectureId],
    );
    await db.run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollmentId, 997.0, 'PAID'],
    );
}

module.exports = { openDatabase, migrate, seed };
