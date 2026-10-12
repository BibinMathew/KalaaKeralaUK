# Stripe setup

Use the club's UK Stripe account and its own settlement bank account. No secret keys are included in this source. Configure secrets in the hosting dashboard or an untracked `.env`.

## Test mode first

1. Set STRIPE_SECRET_KEY to the club's **test** secret key.
2. For local development, use Stripe CLI:
   `stripe listen --forward-to localhost:8000/stripe/webhook/`
3. Set STRIPE_WEBHOOK_SECRET to the CLI's signing secret; restart the application. Hosted test environments use the signing secret for their registered endpoint instead.
4. In Club settings, replace refund terms, set contact details and enable payments.
5. Create a published future event, set its GBP price, and enable booking. Each event has one price per person; visitors choose 1–10 places.
6. Complete a Stripe test checkout and verify the order becomes Paid only after its webhook succeeds. Test declines, cancellation, refresh, duplicate notifications and refunds.
7. Configure Stripe's customer receipt emails. No custom ticket email is sent by this app.

## Production webhook

Register `https://YOUR-DOMAIN/stripe/webhook/` in Stripe for:

- checkout.session.completed
- checkout.session.async_payment_succeeded
- checkout.session.async_payment_failed
- checkout.session.expired
- charge.refunded

Checkout currently requests card payments; delayed-payment webhook cases are handled defensively. Use the live secret key and live endpoint signing secret together when moving to production. Set SITE_URL to the exact HTTPS origin. Never put keys in Git, front-end JavaScript or a screenshot.

## Payment behaviour

The application uses Stripe's official Python SDK. It does not build its own payment form. Prices are server-side GBP values stored in the event or membership settings; visitors cannot override them through form fields. Webhook signatures are checked using the SDK, and completed sessions are fetched from Stripe before confirmation. Amount, currency, mode and order/session identity must match. Repeated webhook deliveries do not duplicate a payment confirmation.

Opening the success URL cannot mark an order as paid. A cancelled checkout remains pending until it expires or payment succeeds. For a different booking, choose **Start a separate booking** on the event page. The previous Stripe session can remain payable until Stripe expires it; warn a customer against paying both sessions if they changed their mind.

Membership payments are one-time application payments, not subscriptions. Membership approval remains a separate admin action. Publish the period, eligibility and refund terms before enabling fees.

Refunds must be initiated in Stripe; the signed `charge.refunded` event updates the order. Partial refunds display a separate status. Keep Stripe as the financial source of truth. Reconcile orders against Stripe before each event; this starter does not include a background reconciliation worker, chargeback dashboard, VAT invoicing, recurring billing or capacity-controlled ticket reservations.

Official integration reference: https://docs.stripe.com/checkout/fulfillment
