from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from club import views
from club.admin import site
urlpatterns=[path('',views.home,name='home'),path('about/',views.about,name='about'),path('office-bearers/',views.committee,name='committee'),path('events/',views.events,name='events'),path('events/<slug:slug>/',views.event_detail,name='event'),path('events/<slug:slug>/calendar.ics',views.event_ics,name='event_ics'),path('events/<slug:slug>/new-booking/',views.new_booking,name='new_booking'),path('gallery/',views.gallery,name='gallery'),path('gallery/<slug:slug>/',views.album,name='album'),path('videos/',views.videos,name='videos'),path('resources/<str:section>/',views.resources,name='resources'),path('membership/',views.membership,name='membership'),path('contact/',views.contact,name='contact'),path('payment/<uuid:order_id>/',views.payment_status,name='payment_status'),path('stripe/webhook/',views.stripe_webhook,name='stripe_webhook'),path('privacy/',views.policy,{'kind':'privacy'},name='privacy'),path('refunds/',views.policy,{'kind':'refunds'},name='refunds'),path('health/',views.health,name='health'),path('admin/',site.urls)]
if settings.DEBUG:urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
