/**
 * The payment port, and the stub that currently stands behind it.
 *
 * The approval rule used to be one expression inside the checkout route handler:
 *
 *     let status = cc.startsWith("4") ? "PAID" : "DENIED";
 *
 * That is not an authorization. It contacts nobody, checks no funds, validates no card and
 * captures nothing — any number beginning with 4 was an approved purchase and a free
 * enrollment. **The rule itself is unchanged here, deliberately**: there is no gateway to
 * integrate with in this project, and silently inventing one would hide the gap. What
 * changed is that it now has a name, a single owner, an interface, and a refusal to run in
 * production — so replacing it is one adapter, not an edit inside a request handler.
 *
 * A real adapter must implement `authorize` and do what the stub cannot: validate the card,
 * call the provider with the configured key, and return the provider's decision plus its
 * reference. Note that it must also stop the card number from reaching the application at
 * all; the stub only tolerates it because it never leaves this module.
 */
const APPROVED_CARD_PREFIX = '4';

/** Last four digits: the most that may be logged or stored about a card. */
function maskCard(cardNumber) {
    return `****${String(cardNumber).slice(-4)}`;
}

function createStubPaymentGateway({ logger }) {
    return {
        name: 'stub',

        async authorize({ cardNumber, amount, reference }) {
            const approved = String(cardNumber).startsWith(APPROVED_CARD_PREFIX);
            logger.warn('payment authorized by stub gateway — no provider was contacted', {
                approved,
                amount,
                reference,
                card: maskCard(cardNumber),
            });
            return {
                approved,
                reference: null,
                declineReason: approved ? null : 'stub_rule_card_prefix',
            };
        },
    };
}

function createPaymentGateway({ config, logger }) {
    if (config.payment.driver === 'stub') {
        if (config.isProduction) {
            throw new Error(
                'PAYMENT_DRIVER=stub refuses to run in production: it approves cards without ' +
                'contacting a provider. Configure a real gateway adapter.',
            );
        }
        logger.warn('using the stub payment gateway', { env: config.env });
        return createStubPaymentGateway({ logger });
    }

    throw new Error(
        `PAYMENT_DRIVER="${config.payment.driver}" has no adapter. Implement one that calls the ` +
        'provider and register it here; the stub is development-only.',
    );
}

module.exports = { createPaymentGateway, createStubPaymentGateway, maskCard, APPROVED_CARD_PREFIX };
