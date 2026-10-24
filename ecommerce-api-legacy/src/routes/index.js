const { Router } = require('express');
const { createCheckoutRoutes } = require('./checkoutRoutes');
const { createAdminRoutes } = require('./adminRoutes');
const { createUserRoutes } = require('./userRoutes');

function createRoutes(deps) {
    const router = Router();
    router.use(createCheckoutRoutes(deps));
    router.use(createAdminRoutes(deps));
    router.use(createUserRoutes(deps));
    return router;
}

module.exports = { createRoutes };
