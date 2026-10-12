from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from club.models import SiteSettings,Event,Resource
class Command(BaseCommand):
    help='Create club settings and optional clearly labelled local demo events.'
    def add_arguments(self,parser):parser.add_argument('--demo',action='store_true')
    def handle(self,*args,**options):
        SiteSettings.objects.get_or_create(pk=1)
        if options['demo']:
            if not settings.DEBUG:raise CommandError('Demo content is allowed only with DEBUG=true. Never seed demo content on production.')
            now=timezone.now()
            for i,(name,category) in enumerate([('Onam celebration','onam'),('Christmas gathering','christmas'),('Community sports day','sports')]):
                start=now+timedelta(days=3+i*7)
                Event.objects.get_or_create(slug=f'demo-{category}',defaults={'title':f'DEMO — {name}','category':category,'description':'Illustrative demo event only. This is not an actual club announcement. Delete or replace it before launch.','starts_at':start,'ends_at':start+timedelta(hours=4),'venue':'Demo venue — not confirmed','published':True,'booking_open':False})
        self.stdout.write(self.style.SUCCESS('Club settings ready. Update content in /admin/.'))
