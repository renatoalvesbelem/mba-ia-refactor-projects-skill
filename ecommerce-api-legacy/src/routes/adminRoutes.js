const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const createRequireAdmin = require('../middlewares/auth');

function createAdminRoutes({ financialReportController, config }) {
    const router = Router();
    const requireAdmin = createRequireAdmin(config);

    router.get('/admin/financial-report', requireAdmin, asyncHandler(async (req, res) => {
        const report = await financialReportController.getReport();
        res.status(200).json(report);
    }));

    return router;
}

module.exports = { createAdminRoutes };
