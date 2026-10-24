function createPaymentModel(db) {
    return {
        create(enrollmentId, amount, status) {
            return db.run(
                'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
                [enrollmentId, amount, status],
            );
        },
        financialReport() {
            return db.all(`
                SELECT
                    courses.id AS course_id,
                    courses.title AS course_title,
                    enrollments.id AS enrollment_id,
                    users.name AS student_name,
                    payments.amount AS paid_amount,
                    payments.status AS payment_status
                FROM courses
                LEFT JOIN enrollments ON enrollments.course_id = courses.id
                LEFT JOIN users ON users.id = enrollments.user_id
                LEFT JOIN payments ON payments.enrollment_id = enrollments.id
                ORDER BY courses.id, enrollments.id
            `);
        },
    };
}

module.exports = { createPaymentModel };
