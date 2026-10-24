function createCourseModel(db) {
    return {
        findActive(id) {
            return db.get('SELECT id, title, price, active FROM courses WHERE id = ? AND active = 1', [id]);
        },
        findAll() {
            return db.all('SELECT id, title, price, active FROM courses ORDER BY id');
        },
    };
}

module.exports = { createCourseModel };
