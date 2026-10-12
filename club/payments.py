import stripe
from django.conf import settings
from django.db import transaction
from .models import Order, StripeEvent

def client():
    stripe.api_key=settings.STRIPE_SECRET_KEY
    stripe.max_network_retries=2
    return stripe

def checkout(order):
    s=client()
    session=s.checkout.Session.create(
        mode='payment',payment_method_types=['card'],customer_email=order.email,
        client_reference_id=str(order.id),metadata={'order_id':str(order.id)},
        payment_intent_data={'metadata':{'order_id':str(order.id)}},
        line_items=[{'price_data':{'currency':'gbp','unit_amount':order.amount_pence//order.quantity,'product_data':{'name':order.description}},'quantity':order.quantity}],
        success_url=settings.SITE_URL+'/payment/'+str(order.id)+'/',
        cancel_url=settings.SITE_URL+'/payment/'+str(order.id)+'/?cancelled=1',
        idempotency_key='checkout-'+str(order.id))
    Order.objects.filter(pk=order.pk).update(stripe_session=session.id)
    return session.url

def process_event(event):
    """A transaction and unique event ID make webhook retries idempotent."""
    kind=event['type']; obj=event['data']['object']
    session=None
    if kind in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
        session=client().checkout.Session.retrieve(obj['id'])
    refund_order_id=None
    if kind=='charge.refunded' and obj.get('payment_intent') and not Order.objects.filter(stripe_payment_intent=obj['payment_intent']).exists():
        intent=client().PaymentIntent.retrieve(obj['payment_intent'])
        refund_order_id=intent.get('metadata',{}).get('order_id')
    with transaction.atomic():
        _,fresh=StripeEvent.objects.get_or_create(pk=event['id'])
        if not fresh:return
        if session:
            order_id=session.get('metadata',{}).get('order_id')
            if not order_id: return
            try: order=Order.objects.select_for_update().get(pk=order_id)
            except (Order.DoesNotExist,ValueError):return
            if session.get('mode')!='payment' or session.get('currency')!='gbp' or session.get('amount_total')!=order.amount_pence:
                raise ValueError('Checkout amount, currency or mode mismatch')
            if order.stripe_session and order.stripe_session!=session['id']:raise ValueError('Checkout session mismatch')
            if session.get('payment_status')=='paid' and order.status not in ('refunded','part_refunded'):
                order.status='paid'; order.stripe_session=session['id'];order.stripe_payment_intent=session.get('payment_intent') or '';order.save(update_fields=['status','stripe_session','stripe_payment_intent'])
        elif kind in ('checkout.session.expired','checkout.session.async_payment_failed'):
            Order.objects.filter(stripe_session=obj['id'],status='pending').update(status='expired' if kind.endswith('expired') else 'failed')
        elif kind=='charge.refunded' and obj.get('payment_intent'):
            orders=Order.objects.filter(pk=refund_order_id) if refund_order_id else Order.objects.filter(stripe_payment_intent=obj['payment_intent'])
            orders.exclude(status='refunded').update(status='refunded' if obj.get('refunded') else 'part_refunded',stripe_payment_intent=obj['payment_intent'])
