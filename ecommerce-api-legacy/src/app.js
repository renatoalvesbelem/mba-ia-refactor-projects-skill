const express = require('express');
const { createRoutes } = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const { createUserModel } = require('./models/userModel');
const { createCourseModel } = require('./models/courseModel');
const { createEnrollmentModel } = require('./models/enrollmentModel');
const { createPaymentModel } = require('./models/paymentModel');
const { createAuditLogModel } = require('./models/auditLogModel');
const { createCheckoutController } = require('./controllers/checkoutController');
const { createFinancialReportController } = require('./controllers/financialReportController');
const { createUserController } = require('./controllers/userController');
const { createPaymentGateway } = require('./services/paymentGateway');
const passwordHasher = require('./services/passwordHasher');

function createApp({ db, config }) {
    const app = express();
    app.use(express.json());

    const paymentModel = createPaymentModel(db);
    const userModel = createUserModel(db);
    const courseModel = createCourseModel(db);
    const enrollmentModel = createEnrollmentModel(db, { paymentModel });
    const auditLogModel = createAuditLogModel(db);
    const paymentGateway = createPaymentGateway();

    const checkoutController = createCheckoutController({
        courseModel,
        userModel,
        enrollmentModel,
        auditLogModel,
        paymentGateway,
        passwordHasher,
    });
    const financialReportController = createFinancialReportController({ paymentModel });
    const userController = createUserController({ userModel });

    app.use('/api', createRoutes({
        checkoutController,
        financialReportController,
        userController,
        config,
    }));

    app.use(errorHandler);

    return app;
}

module.exports = { createApp };
