/**
 * The payment port, and the placeholder that stands behind it until a provider is integrated.
 *
 * The approval rule used to be one expression inside the checkout route handler:
 *
 *     let status = cc.startsWith("4") ? "PAID" : "DENIED";
 *
 * Extracting it into this module gave it an owner and an interface, which fixed where the
 * rule lived. It did not fix the rule: any number beginning with 4 was still an approved
 * purchase and a free enrollment, and `PAYMENT_DRIVER` selected this path by default in every
 * environment that was not literally 'production'. A forged authorization behind a clean
 * interface is still a forged authorization.
 *
 * So the placeholder no longer decides. It cannot contact a provider, validate a card or
 * capture funds, and the only answer it can honestly give is a decline — which is also the
 * safe one, because the capability it cannot verify is the capability it must not grant. The
 * card number is no longer an input to the decision, so there is no rule left to discover.
 *
 * `PAYMENT_STUB_APPROVE=true` exists for developing the flow that follows a successful
 * payment. It is named for what it does, it is off unless set, and `config` honours it only
 * when NODE_ENV is 'development'.
 *
 * A real adapter implements `authorize({ cardNumber, amount, reference })` and returns the
 * provider's decision plus its reference. It must also keep the card number out of the
 * application: the only reason the PAN reaches this layer today is that nothing here uses it.
 */
const DECLINE_NO_GATEWAY = 'no_payment_gateway_configured';

function createStubPaymentGateway({ logger, approveForDevelopment }) {
    if (approveForDevelopment) {
        logger.warn(
            'PAYMENT_STUB_APPROVE is on: the stub will approve every charge without ' +
            'contacting a provider. Development only.',
        );
    }

    return {
        name: 'stub',
        approves: Boolean(approveForDevelopment),

        /**
         * `cardNumber` is accepted so the port matches what a real adapter needs, and is
         * deliberately unused: nothing here is capable of judging it.
         */
        async authorize({ amount, reference }) {
            if (!approveForDevelopment) {
                logger.warn('payment declined: no gateway adapter is configured', {
                    amount,
                    reference,
                });
                return {
                    approved: false,
                    reference: null,
                    declineReason: DECLINE_NO_GATEWAY,
                };
            }

            logger.warn('payment APPROVED BY STUB — no provider was contacted', {
                amount,
                reference,
            });
            return { approved: true, reference: null, declineReason: null };
        },
    };
}

function createPaymentGateway({ config, logger }) {
    if (config.payment.driver === 'stub') {
        if (config.isProduction) {
            throw new Error(
                'PAYMENT_DRIVER=stub refuses to run in production: it cannot authorize a ' +
                'payment. Configure a real gateway adapter.',
            );
        }

        // A key set against the stub means someone believes a provider is wired up. Nothing
        // here would use it, so say so rather than letting the assumption stand.
        if (config.payment.gatewayKey) {
            logger.warn(
                'PAYMENT_GATEWAY_KEY is set but PAYMENT_DRIVER=stub, which contacts no ' +
                'provider and ignores the key. No payment will be authorized against it.',
            );
        }

        logger.warn('using the stub payment gateway: every charge is declined', {
            env: config.env,
            approvesForDevelopment: config.payment.stubApprove,
        });
        return createStubPaymentGateway({
            logger,
            approveForDevelopment: config.payment.stubApprove,
        });
    }

    throw new Error(
        `PAYMENT_DRIVER="${config.payment.driver}" has no adapter. Implement one that calls ` +
        'the provider and register it here; the stub is development-only.',
    );
}

module.exports = {
    createPaymentGateway,
    createStubPaymentGateway,
    DECLINE_NO_GATEWAY,
};
