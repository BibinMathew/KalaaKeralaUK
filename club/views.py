import calendar, hashlib, logging, uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import never_cache
from .models import *
from .forms import MembershipForm, EnquiryForm, BookingForm
from . import payments
logger=logging.getLogger(__name__)

def limited(request,scope,limit=10):
    raw=request.META.get('REMOTE_ADDR','unknown')
    digest=hashlib.sha256((settings.SECRET_KEY+raw).encode()).hexdigest()[:32]
    key=f'{scope}:{digest}:{int(timezone.now().timestamp())//3600}'
    b,_=RateBucket.objects.get_or_create(key=key)
    RateBucket.objects.filter(pk=b.pk).update(count=F('count')+1)
    b.refresh_from_db();return b.count>limit

def notify(subject,body):
    email=SiteSettings.current().contact_email
    if email:
        try:send_mail(subject,body,settings.DEFAULT_FROM_EMAIL,[email])
        except Exception:logger.exception('Admin notification failed; submission remains stored in the admin dashboard.')

def home(request):
    return render(request,'club/home.html',{'events':Event.objects.filter(published=True,ends_at__gte=timezone.now())[:3],'albums':Album.objects.filter(published=True).prefetch_related('photos')[:3],'committee':CommitteeMember.objects.filter(published=True)[:4],'resources':Resource.objects.filter(published=True,section='community')[:3]})

def about(request):return render(request,'club/about.html')
def committee(request):return render(request,'club/committee.html',{'people':CommitteeMember.objects.filter(published=True)})

def events(request):
    today=timezone.localdate()
    try:
        year=int(request.GET.get('year',today.year));month=int(request.GET.get('month',today.month))
        if not 2000<=year<=2100 or not 1<=month<=12:raise ValueError()
    except ValueError:return HttpResponseBadRequest('Invalid calendar month.')
    start=datetime(year,month,1,tzinfo=ZoneInfo('Europe/London'))
    next_month=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
    prev=(start-timedelta(days=1))
    qs=Event.objects.filter(published=True)
    category=request.GET.get('category','')
    if category: qs=qs.filter(category=category)
    q=request.GET.get('q','').strip()[:100]
    if q:qs=qs.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(venue__icontains=q))
    month_events=list(qs.filter(starts_at__lt=next_month,ends_at__gte=start))
    weeks=[]
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year,month):
        cells=[]
        for day in week:
            dayevents=[e for e in month_events if day and timezone.localtime(e.starts_at).date()<=start.replace(day=day).date()<=timezone.localtime(e.ends_at).date()]
            cells.append({'day':day,'events':dayevents,'today':day and today==start.replace(day=day).date()})
        weeks.append(cells)
    past=request.GET.get('period')=='past'
    listing=qs.filter(ends_at__lt=timezone.now()).order_by('-starts_at') if past else qs.filter(ends_at__gte=timezone.now())
    return render(request,'club/events.html',{'weeks':weeks,'month_name':start.strftime('%B %Y'),'previous':prev,'next_month':next_month,'categories':Event.CATEGORY,'category':category,'query':q,'events':listing,'past':past})

@never_cache
def event_detail(request,slug):
    event=get_object_or_404(Event,slug=slug,published=True)
    token_key='booking_'+str(event.pk)
    if token_key not in request.session:request.session[token_key]=str(uuid.uuid4())
    form=BookingForm(request.POST or None)
    if request.method=='POST':
        if limited(request,'booking'):return HttpResponse('Too many attempts. Please try again later.',status=429)
        club=SiteSettings.current()
        if not event.bookable:form.add_error(None,'Bookings are currently closed.')
        elif event.price and not (club.payments_enabled and settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET):form.add_error(None,'Online payments are not available yet. Please contact the club.')
        elif form.is_valid():
            data=form.cleaned_data
            with transaction.atomic():
                order,created=Order.objects.get_or_create(checkout_token=request.session[token_key],defaults={'event':event,'name':data['name'],'email':data['email'],'quantity':data['quantity'],'amount_pence':int(event.price*100)*data['quantity'],'description':event.title+' — '+event.payment_purpose,'status':'pending' if event.price else 'free'})
            if not created and (order.quantity!=data['quantity'] or order.email!=data['email'] or order.name!=data['name'] or order.amount_pence!=int(event.price*100)*data['quantity']):
                form.add_error(None,'A previous booking is in progress. Open its confirmation or start a new booking below.')
            elif order.status!='pending':return redirect('payment_status',order_id=order.id)
            else:
                try:return redirect(payments.checkout(order))
                except Exception:logger.exception('Stripe checkout creation failed');form.add_error(None,'Checkout could not be opened. Your card has not been charged here. Please retry or contact the club.')
            if order.status=='free':return redirect('payment_status',order_id=order.id)
    return render(request,'club/event.html',{'event':event,'form':form,'albums':event.album_set.filter(published=True)})

@require_POST
def new_booking(request,slug):
    event=get_object_or_404(Event,slug=slug,published=True)
    request.session['booking_'+str(event.pk)]=str(uuid.uuid4())
    return redirect('event',slug=slug)

def event_ics(request,slug):
    event=get_object_or_404(Event,slug=slug,published=True)
    def esc(s):return s.replace('\\','\\\\').replace('\r','').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
    def dt(d):return d.astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Kalaa Kerala//Community Events//EN','BEGIN:VEVENT',f'UID:event-{event.pk}@kalaa-kerala',f'DTSTAMP:{dt(timezone.now())}',f'DTSTART:{dt(event.starts_at)}',f'DTEND:{dt(event.ends_at)}','SUMMARY:'+esc(event.title),'LOCATION:'+esc(event.venue+' '+event.address),'DESCRIPTION:'+esc(event.description),'END:VEVENT','END:VCALENDAR']
    # Fold long UTF-8 lines to stay within the iCalendar 75-octet limit.
    folded=[]
    for line in lines:
        chunk=''
        for char in line:
            if len((chunk+char).encode())>74:folded.append(chunk);chunk=' '+char
            else:chunk+=char
        folded.append(chunk)
    response=HttpResponse('\r\n'.join(folded)+'\r\n',content_type='text/calendar; charset=utf-8')
    response['Content-Disposition']=f'attachment; filename="{event.slug}.ics"'
    return response

def gallery(request):return render(request,'club/gallery.html',{'albums':Album.objects.filter(published=True).prefetch_related('photos')})
def album(request,slug):return render(request,'club/album.html',{'album':get_object_or_404(Album,slug=slug,published=True)})
def videos(request):return render(request,'club/videos.html',{'videos':Video.objects.filter(published=True)})
def resources(request,section):
    titles=dict(Resource.SECTION)
    if section not in titles:return HttpResponse(status=404)
    return render(request,'club/resources.html',{'title':titles[section],'section':section,'resources':Resource.objects.filter(section=section,published=True)})

@never_cache
def membership(request):
    club=SiteSettings.current();form=MembershipForm(request.POST or None)
    if 'member_token' not in request.session:request.session['member_token']=str(uuid.uuid4())
    if request.method=='POST':
        if limited(request,'membership',5):return HttpResponse('Too many submissions. Please try again later.',status=429)
        if not club.membership_open:form.add_error(None,'Membership applications are not open yet.')
        elif club.membership_fee and not (club.payments_enabled and settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET):form.add_error(None,'Membership payments are not available yet.')
        elif form.is_valid():
            with transaction.atomic():
                order=Order.objects.filter(checkout_token=request.session['member_token']).first()
                if not order:
                    member=form.save()
                    order=Order.objects.create(checkout_token=request.session['member_token'],membership=member,name=member.name,email=member.email,amount_pence=int(club.membership_fee*100),description='Kalaa Kerala membership application',status='pending' if club.membership_fee else 'free')
                    transaction.on_commit(lambda:notify('New membership application','A new membership application is awaiting review in the club admin dashboard.'))
            if order.status!='pending':return redirect('payment_status',order_id=order.id)
            try:return redirect(payments.checkout(order))
            except Exception:logger.exception('Membership checkout failed');form.add_error(None,'Your application is saved but checkout is unavailable. Retry with the same details or contact the club.')
    return render(request,'club/membership.html',{'form':form})

def contact(request):
    form=EnquiryForm(request.POST or None)
    if request.method=='POST':
        if limited(request,'contact',5):return HttpResponse('Too many messages. Please try again later.',status=429)
        if not SiteSettings.current().contact_open:form.add_error(None,'Please contact us through Facebook until the enquiry form opens.')
        elif form.is_valid():
            form.save();notify('New website enquiry','A new enquiry is available in the club admin dashboard.');messages.success(request,'Thank you. Your enquiry has been saved for the club team.');return redirect('contact')
    return render(request,'club/contact.html',{'form':form})

@never_cache
def payment_status(request,order_id):
    order=get_object_or_404(Order,pk=order_id)
    tokens=[value for key,value in request.session.items() if key.startswith('booking_') or key=='member_token']
    if str(order.checkout_token) not in tokens:return HttpResponseForbidden('Open this confirmation in the browser where you started the booking. Contact the club if you need help.')
    return render(request,'club/payment.html',{'order':order,'cancelled':request.GET.get('cancelled')=='1'})

@csrf_exempt
@require_POST
def stripe_webhook(request):
    import stripe
    if not settings.STRIPE_WEBHOOK_SECRET:return HttpResponse(status=503)
    try:event=stripe.Webhook.construct_event(request.body,request.headers.get('Stripe-Signature',''),settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError,stripe.SignatureVerificationError):return HttpResponseBadRequest('Invalid signature or payload')
    try:payments.process_event(event)
    except Exception:logger.exception('Stripe webhook processing failed');return HttpResponse(status=500)
    return HttpResponse(status=200)

def policy(request,kind):return render(request,'club/policy.html',{'title':'Privacy notice' if kind=='privacy' else 'Cancellation & refunds','body':getattr(SiteSettings.current(),'privacy' if kind=='privacy' else 'refund_policy')})
@require_GET
def health(request):return HttpResponse('ok',content_type='text/plain')
