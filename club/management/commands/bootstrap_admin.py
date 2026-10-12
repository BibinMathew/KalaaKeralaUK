"""Create the designated admin once, without a hosted interactive shell."""
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the first admin from ADMIN_INITIAL_PASSWORD; never reset existing accounts.'

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username=settings.ADMIN_USERNAME).exists():
            return
        password = os.getenv('ADMIN_INITIAL_PASSWORD', '')
        if not password:
            self.stdout.write('No initial admin password supplied; bootstrap skipped.')
            return
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError('An administrator already exists; refusing to create another.')
        user = User(username=settings.ADMIN_USERNAME, email=os.getenv('ADMIN_EMAIL', ''))
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError('Initial admin password failed validation.') from exc
        User.objects.create_superuser(username=user.username, email=user.email, password=password)
        self.stdout.write('Initial administrator created. Remove ADMIN_INITIAL_PASSWORD from hosting settings.')
