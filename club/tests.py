import io, json, uuid, hmac, hashlib, time, tempfile
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import *
from .payments import process_event
from .admin import safe_csv

@override_settings(SECURE_SSL_REDIRECT=False,STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ClubTests(TestCase):
    def setUp(self):
        self.club=SiteSettings.objects.create(membership_open=True,contact_open=True,payments_enabled=True)
        self.event=Event.objects.create(title='Test event',slug='test-event',description='A real description',starts_at=timezone.now()+timedelta(days=10),ends_at=timezone.now()+timedelta(days=10,hours=3),venue='Hall',published=True,booking_open=True)
    def booking(self,**extra):return {'name':'Test Person','email':'test@example.com','quantity':2,'consent':'on',**extra}
    def order(self,**extra):return Order.objects.create(checkout_token=uuid.uuid4(),event=self.event,name='Test',email='test@example.com',amount_pence=2500,description='Event',**extra)
    def test_public_pages_render(self):
        for path in ['/','/about/','/office-bearers/','/events/','/gallery/','/videos/','/membership/','/contact/','/resources/learning/','/resources/links/','/resources/newcomers/','/privacy/','/refunds/','/events/test-event/']:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
    def test_calendar_leap_year_and_month_validation(self):
        response=self.client.get('/events/?year=2028&month=2')
        self.assertContains(response,'February 2028');self.assertContains(response,'>29</span>')
        self.assertEqual(self.client.get('/events/?month=13').status_code,400)
    def test_calendar_contains_event_and_filter_works(self):
        response=self.client.get(f'/events/?year={self.event.starts_at.year}&month={self.event.starts_at.month}')
        self.assertContains(response,'Test event')
        self.assertNotContains(self.client.get('/events/?category=christmas'),'Test event')
    def test_drafts_not_public(self):
        self.event.published=False;self.event.save()
        self.assertEqual(self.client.get('/events/test-event/').status_code,404)
        self.assertNotContains(self.client.get('/events/'),'Test event')
    def test_free_booking_persists_once(self):
        self.client.get('/events/test-event/')
        for _ in range(2):self.assertEqual(self.client.post('/events/test-event/',self.booking()).status_code,302)
        self.assertEqual(Order.objects.count(),1);self.assertEqual(Order.objects.get().status,'free')
    def test_invalid_quantity_rejected(self):
        self.client.post('/events/test-event/',self.booking(quantity=0))
        self.assertEqual(Order.objects.count(),0)
    def test_past_event_cannot_book(self):
        self.event.starts_at=timezone.now()-timedelta(hours=3);self.event.ends_at=timezone.now()-timedelta(hours=1);self.event.save()
        self.client.post('/events/test-event/',self.booking());self.assertEqual(Order.objects.count(),0)
    def test_csrf_enforced(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/events/test-event/',self.booking()).status_code,403)
    @override_settings(STRIPE_SECRET_KEY='sk_test_fake',STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('club.payments.stripe.checkout.Session.create')
    def test_price_comes_from_database(self,create):
        create.return_value=SimpleNamespace(id='cs_test_1',url='https://checkout.stripe.com/test')
        self.event.price=Decimal('25.00');self.event.save()
        response=self.client.post('/events/test-event/',self.booking(amount_pence=1,price='0.01'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(Order.objects.get().amount_pence,5000)
        self.assertEqual(create.call_args.kwargs['line_items'][0]['price_data']['unit_amount'],2500)
    def test_paid_checkout_requires_configuration(self):
        self.event.price=Decimal('25');self.event.save()
        self.client.post('/events/test-event/',self.booking());self.assertEqual(Order.objects.count(),0)
    def test_membership_submission_and_duplicate(self):
        data={'name':'Applicant','email':'member@example.com','area':'Mansfield','household_size':3,'consent':'on'}
        self.client.get('/membership/')
        self.assertEqual(self.client.post('/membership/',data).status_code,302)
        self.client.post('/membership/',data)
        self.assertEqual(Membership.objects.count(),1);self.assertEqual(Membership.objects.get().status,'pending')
    def test_membership_closed(self):
        self.club.membership_open=False;self.club.save()
        self.client.post('/membership/',{'name':'A','email':'a@example.com','area':'Ashfield','household_size':1,'consent':'on'})
        self.assertFalse(Membership.objects.exists())
    def test_honeypot_rejected(self):
        self.client.post('/contact/',{'name':'Bot','email':'b@example.com','subject':'Hi','message':'spam','consent':'on','website':'spam'})
        self.assertFalse(Enquiry.objects.exists())
    def test_contact_submission_and_rate_limit(self):
        data={'name':'Visitor','email':'v@example.com','subject':'Enquiry','message':'Hello club','consent':'on'}
        for _ in range(5):self.assertEqual(self.client.post('/contact/',data).status_code,302)
        self.assertEqual(self.client.post('/contact/',data).status_code,429)
    def test_anonymous_admin_denied(self):self.assertEqual(self.client.get('/admin/club/event/add/').status_code,302)
    def test_only_designated_admin(self):
        user=get_user_model().objects.create_superuser(username='otheradmin',password='test-password-unused',email='x@example.com')
        self.client.force_login(user);self.assertEqual(self.client.get('/admin/').status_code,302)
        user.username='clubadmin';user.save();self.assertEqual(self.client.get('/admin/').status_code,200)
    def test_ics_escapes_injected_lines(self):
        self.event.title='Meeting\nBEGIN:VEVENT';self.event.save()
        response=self.client.get('/events/test-event/calendar.ics')
        self.assertContains(response,'SUMMARY:Meeting\\nBEGIN:VEVENT');self.assertEqual(response.content.count(b'\r\nBEGIN:VEVENT'),1)
    def test_private_order_cannot_be_read_in_another_session(self):
        order=self.order();self.assertEqual(self.client.get(f'/payment/{order.id}/').status_code,403)
    def test_forged_success_does_not_mark_paid(self):
        order=self.order();session=self.client.session;session['booking_1']=str(order.checkout_token);session.save()
        self.assertEqual(self.client.get(f'/payment/{order.id}/?paid=true').status_code,200)
        order.refresh_from_db();self.assertEqual(order.status,'pending')
    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    def test_bad_webhook_signature(self):
        response=self.client.post('/stripe/webhook/',data='{}',content_type='application/json',HTTP_STRIPE_SIGNATURE='bad')
        self.assertEqual(response.status_code,400)
    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test',STRIPE_SECRET_KEY='sk_test_fake')
    @patch('club.payments.stripe.checkout.Session.retrieve')
    def test_signed_webhook_and_duplicate(self,retrieve):
        order=self.order(stripe_session='cs_test_2')
        retrieve.return_value={'id':'cs_test_2','metadata':{'order_id':str(order.id)},'mode':'payment','currency':'gbp','amount_total':2500,'payment_status':'paid','payment_intent':'pi_2'}
        body=json.dumps({'id':'evt_test','type':'checkout.session.completed','data':{'object':{'id':'cs_test_2'}}})
        timestamp=int(time.time());sig=hmac.new(b'whsec_test',f'{timestamp}.{body}'.encode(),hashlib.sha256).hexdigest()
        for _ in range(2):self.assertEqual(self.client.post('/stripe/webhook/',data=body,content_type='application/json',HTTP_STRIPE_SIGNATURE=f't={timestamp},v1={sig}').status_code,200)
        order.refresh_from_db();self.assertEqual(order.status,'paid');self.assertEqual(StripeEvent.objects.count(),1)
    @patch('club.payments.stripe.checkout.Session.retrieve')
    def test_wrong_amount_rejected(self,retrieve):
        order=self.order();retrieve.return_value={'id':'cs_fake','metadata':{'order_id':str(order.id)},'mode':'payment','currency':'gbp','amount_total':1,'payment_status':'paid'}
        with self.assertRaises(ValueError):process_event({'id':'evt_wrong','type':'checkout.session.completed','data':{'object':{'id':'cs_fake'}}})
        order.refresh_from_db();self.assertEqual(order.status,'pending');self.assertFalse(StripeEvent.objects.exists())
    @patch('club.payments.stripe.checkout.Session.retrieve')
    def test_unpaid_session_stays_pending(self,retrieve):
        order=self.order();retrieve.return_value={'id':'cs_pending','metadata':{'order_id':str(order.id)},'mode':'payment','currency':'gbp','amount_total':2500,'payment_status':'unpaid'}
        process_event({'id':'evt_pending','type':'checkout.session.completed','data':{'object':{'id':'cs_pending'}}})
        order.refresh_from_db();self.assertEqual(order.status,'pending')
    def test_refund_status(self):
        order=self.order(status='paid',stripe_payment_intent='pi_refund')
        process_event({'id':'evt_refund','type':'charge.refunded','data':{'object':{'payment_intent':'pi_refund','refunded':True}}})
        order.refresh_from_db();self.assertEqual(order.status,'refunded')
    def test_invalid_image_rejected(self):
        with self.assertRaises(ValidationError):validate_image(SimpleUploadedFile('x.jpg',b'<script>bad</script>'))
    def test_image_reencoded(self):
        out=io.BytesIO();Image.new('RGB',(2200,1100),'green').save(out,format='PNG')
        album=Album.objects.create(title='Photos',slug='photos')
        photo=Photo.objects.create(album=album,image=SimpleUploadedFile('test.png',out.getvalue(),content_type='image/png'))
        with Image.open(photo.image) as image:self.assertEqual(image.format,'JPEG');self.assertLessEqual(image.width,2000)
    def test_unsafe_video_rejected(self):
        with self.assertRaises(ValidationError):Video(title='unsafe',url='https://evil.example/embed').full_clean()
    def test_csv_formula_escaped(self):self.assertEqual(safe_csv('=1+1'),"'=1+1")
    def test_populated_gallery_and_video_pages(self):
        album=Album.objects.create(title='Community album',slug='community',published=True)
        image=io.BytesIO();Image.new('RGB',(20,20),'gold').save(image,'JPEG')
        Photo.objects.create(album=album,caption='Together',image=SimpleUploadedFile('photo.jpg',image.getvalue(),content_type='image/jpeg'))
        Video.objects.create(title='Community video',url='https://youtu.be/abcdefghijk',published=True)
        CommitteeMember.objects.create(name='Example officer',role='Test role',published=True)
        Resource.objects.create(section='learning',title='Test class',body='Details',published=True)
        for url in ['/','/gallery/','/gallery/community/','/videos/','/office-bearers/','/resources/learning/']:
            with self.subTest(url=url):self.assertEqual(self.client.get(url).status_code,200)
    def test_admin_batch_upload(self):
        user=get_user_model().objects.create_superuser(username='clubadmin',password='local-test-only-password',email='admin@example.com')
        self.client.force_login(user)
        album=Album.objects.create(title='Batch',slug='batch')
        image=io.BytesIO();Image.new('RGB',(20,20),'green').save(image,'PNG')
        files=[SimpleUploadedFile(f'p{i}.png',image.getvalue(),content_type='image/png') for i in range(2)]
        response=self.client.post(f'/admin/club/album/{album.pk}/upload/',{'images':files})
        self.assertEqual(response.status_code,302);self.assertEqual(album.photos.count(),2)
    @override_settings(STRIPE_SECRET_KEY='sk_test_fake',STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('club.payments.stripe.checkout.Session.create')
    def test_paid_membership_is_pending_approval(self,create):
        self.club.membership_fee=Decimal('30');self.club.save()
        create.return_value=SimpleNamespace(id='cs_membership',url='https://checkout.stripe.com/test')
        response=self.client.post('/membership/',{'name':'Applicant','email':'member@example.com','area':'Mansfield','household_size':2,'consent':'on'})
        self.assertEqual(response.status_code,302);self.assertEqual(Order.objects.get().amount_pence,3000)
        self.assertEqual(Membership.objects.get().status,'pending')
    @patch('club.payments.stripe.PaymentIntent.retrieve')
    def test_refund_before_completion(self,retrieve):
        order=self.order();retrieve.return_value={'metadata':{'order_id':str(order.pk)}}
        process_event({'id':'evt_early_refund','type':'charge.refunded','data':{'object':{'payment_intent':'pi_early','refunded':True}}})
        order.refresh_from_db();self.assertEqual(order.status,'refunded')

@override_settings(ADMIN_USERNAME='clubadmin')
class BootstrapAdminTests(TestCase):
    def command(self):
        from django.core.management import call_command
        call_command('bootstrap_admin', stdout=io.StringIO())

    @patch.dict('os.environ', {'ADMIN_INITIAL_PASSWORD': 'Review-Secure-9472!phrase'})
    def test_create_once_never_reset(self):
        self.command()
        user = get_user_model().objects.get(username='clubadmin')
        self.assertTrue(user.is_superuser and user.is_staff)
        original = user.password
        with patch.dict('os.environ', {'ADMIN_INITIAL_PASSWORD': 'Other-Secure-8461!phrase'}):
            self.command()
        user.refresh_from_db()
        self.assertEqual(user.password, original)
        self.assertEqual(get_user_model().objects.count(), 1)

    @patch.dict('os.environ', {'ADMIN_INITIAL_PASSWORD': 'short'})
    def test_reject_weak_password(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.command()
        self.assertFalse(get_user_model().objects.exists())

    @patch.dict('os.environ', {'ADMIN_INITIAL_PASSWORD': 'Review-Secure-9472!phrase'})
    def test_refuse_second_admin(self):
        from django.core.management.base import CommandError
        get_user_model().objects.create_superuser('existing', password='Different-9472!phrase')
        with self.assertRaises(CommandError):
            self.command()

    @patch.dict('os.environ', {'ADMIN_INITIAL_PASSWORD': ''})
    def test_no_password_no_account(self):
        self.command()
        self.assertFalse(get_user_model().objects.exists())
