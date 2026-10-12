from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from club.models import RateBucket
class Command(BaseCommand):
    help='Remove old anonymous rate-limit counters. Does not delete member or financial records.'
    def handle(self,*a,**kw):
        count,_=RateBucket.objects.filter(created_at__lt=timezone.now()-timedelta(days=2)).delete()
        self.stdout.write(f'Removed {count} old rate-limit counters.')
