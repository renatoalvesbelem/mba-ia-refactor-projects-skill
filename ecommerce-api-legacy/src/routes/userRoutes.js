const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const createRequireAdmin = require('../middlewares/auth');

function createUserRoutes({ userController, config }) {
    const router = Router();
    const requireAdmin = createRequireAdmin(config);

    router.delete('/users/:id', requireAdmin, asyncHandler(async (req, res) => {
        const result = await userController.remove(req.params.id);
        res.status(200).send(result.message);
    }));

    return router;
}

module.exports = { createUserRoutes };
