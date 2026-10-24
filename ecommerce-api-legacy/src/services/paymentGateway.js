const CARD_APPROVED_PREFIX = '4';

function createPaymentGateway() {
    return {
        charge(card) {
            const approved = String(card).startsWith(CARD_APPROVED_PREFIX);
            return { approved, status: approved ? 'PAID' : 'DENIED' };
        },
    };
}

module.exports = { createPaymentGateway };
