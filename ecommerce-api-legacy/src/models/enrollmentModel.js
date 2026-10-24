function createEnrollmentModel(db, { paymentModel }) {
    return {
        async enrollWithPayment({ userId, courseId, amount, status }) {
            await db.run('BEGIN');
            try {
                const { lastID: enrollmentId } = await db.run(
                    'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
                    [userId, courseId],
                );
                await paymentModel.create(enrollmentId, amount, status);
                await db.run('COMMIT');
                return { enrollmentId };
            } catch (err) {
                await db.run('ROLLBACK');
                throw err;
            }
        },
    };
}

module.exports = { createEnrollmentModel };
