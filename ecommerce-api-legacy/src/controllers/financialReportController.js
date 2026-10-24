function createFinancialReportController({ paymentModel }) {
    return {
        async getReport() {
            const rows = await paymentModel.financialReport();
            const byCourse = new Map();

            for (const row of rows) {
                if (!byCourse.has(row.course_id)) {
                    byCourse.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
                }

                if (row.enrollment_id === null) continue;

                const courseData = byCourse.get(row.course_id);
                if (row.payment_status === 'PAID') {
                    courseData.revenue += row.paid_amount;
                }
                courseData.students.push({
                    student: row.student_name || 'Unknown',
                    paid: row.paid_amount || 0,
                });
            }

            return Array.from(byCourse.values());
        },
    };
}

module.exports = { createFinancialReportController };
