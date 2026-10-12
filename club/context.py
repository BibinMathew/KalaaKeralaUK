from .models import SiteSettings
from django.conf import settings
def site_context(request):
    return {'club':SiteSettings.current(),'stripe_ready':bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET),'current_year':__import__('datetime').date.today().year}
