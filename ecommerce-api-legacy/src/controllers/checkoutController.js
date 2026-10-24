const { NotFoundError, PaymentDeniedError } = require('../errors');
const logger = require('../logger');

const DEFAULT_PASSWORD = '123456';

function maskCard(card) {
    const digits = String(card);
    return `****${digits.slice(-4)}`;
}

function createCheckoutController({ courseModel, userModel, enrollmentModel, auditLogModel, paymentGateway, passwordHasher }) {
    return {
        async checkout({ name, email, password, courseId, card }) {
            const course = await courseModel.findActive(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            let user = await userModel.findByEmail(email);
            if (!user) {
                const passwordHash = passwordHasher.hash(password || DEFAULT_PASSWORD);
                user = await userModel.create({ name, email, passwordHash });
            }

            const charge = paymentGateway.charge(card);
            logger.info('checkout payment attempt', { card: maskCard(card), status: charge.status });

            if (!charge.approved) throw new PaymentDeniedError('Pagamento recusado');

            const { enrollmentId } = await enrollmentModel.enrollWithPayment({
                userId: user.id,
                courseId: course.id,
                amount: course.price,
                status: charge.status,
            });

            await auditLogModel.create(`Checkout curso ${course.id} por ${user.id}`);

            return { enrollmentId };
        },
    };
}

module.exports = { createCheckoutController };
