const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const { parseCheckoutInput } = require('../validators/checkoutValidator');

function createCheckoutRoutes({ checkoutController }) {
    const router = Router();

    router.post('/checkout', asyncHandler(async (req, res) => {
        const input = parseCheckoutInput(req.body);
        const result = await checkoutController.checkout(input);
        res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
    }));

    return router;
}

module.exports = { createCheckoutRoutes };
