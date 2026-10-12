import io, uuid
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from PIL import Image, ImageOps, UnidentifiedImageError
from django.db import models
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

def validate_image(value):
    if value.size > 10*1024*1024: raise ValidationError('Each image must be under 10 MB.')
    try:
        value.seek(0)
        with Image.open(value) as im:
            if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>25000000:
                raise ValidationError('Use a JPEG, PNG or WebP image under 25 megapixels.')
            im.verify()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValidationError('The image file is invalid.') from exc
    finally: value.seek(0)

def image_path(instance,name): return f'photos/{uuid.uuid4().hex}.jpg'

class ImageModel(models.Model):
    image = models.ImageField(upload_to=image_path,validators=[validate_image],blank=True)
    class Meta: abstract=True
    def save(self,*args,**kwargs):
        if self.image and not self.image._committed:
            validate_image(self.image)
            im=ImageOps.exif_transpose(Image.open(self.image)).convert('RGB')
            im.thumbnail((2000,2000))
            out=io.BytesIO(); im.save(out,format='JPEG',quality=85,optimize=True)
            self.image.save(uuid.uuid4().hex+'.jpg',ContentFile(out.getvalue()),save=False)
        super().save(*args,**kwargs)

class SiteSettings(ImageModel):
    name=models.CharField(max_length=160,default='Kalaa Kerala')
    tagline=models.CharField(max_length=240,default='Our roots. Our people. Our community.')
    about=models.TextField(default='Kalaa Kerala Arts & Sports Club brings the Kerala community together in Ashfield and Mansfield, United Kingdom. Our annual Onam and Christmas celebrations create space for connection, culture and shared memories.')
    contact_email=models.EmailField(blank=True)
    phone=models.CharField(max_length=40,blank=True)
    address=models.CharField(max_length=300,default='Ashfield & Mansfield, United Kingdom')
    facebook=models.URLField(default='https://www.facebook.com/profile.php?id=61573813370151')
    instagram=models.URLField(blank=True)
    youtube=models.URLField(blank=True)
    whatsapp=models.URLField(blank=True)
    membership_open=models.BooleanField(default=False,help_text='Enable after reviewing membership terms and the privacy notice.')
    membership_fee=models.DecimalField(max_digits=8,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    membership_terms=models.TextField(default='Applications are reviewed by the club administrator. Membership is confirmed only after approval. Contact the club for the membership period and applicable conditions.')
    privacy=models.TextField(default='We use the details you provide to handle membership applications, event bookings and enquiries. Payment card details are handled by Stripe and are not stored on this website. Contact the club to ask about your information or request a correction. Before public launch, the club must complete this notice with its contact address, purposes and lawful bases, retention periods, service providers, individual rights and complaint information.')
    refund_policy=models.TextField(default='Please contact the club before purchasing if you need information about cancellations or refunds. The club must publish its approved event cancellation and refund terms before enabling paid bookings.')
    payments_enabled=models.BooleanField(default=False,help_text='Enable only after publishing refund terms and testing Stripe and webhooks.')
    contact_open=models.BooleanField(default=False,help_text='Enable after publishing the club contact details and privacy notice.')
    def clean(self):
        if 0 < self.membership_fee < Decimal('0.30'): raise ValidationError('A paid membership fee must be at least £0.30.')
    def save(self,*a,**kw): self.pk=1; super().save(*a,**kw)
    def __str__(self): return 'Club settings'
    @classmethod
    def current(cls): return cls.objects.filter(pk=1).first() or cls()

class Event(ImageModel):
    CATEGORY=[('onam','Onam'),('christmas','Christmas'),('sports','Sports'),('culture','Arts & culture'),('community','Community')]
    title=models.CharField(max_length=160)
    slug=models.SlugField(unique=True)
    category=models.CharField(max_length=20,choices=CATEGORY,default='community')
    description=models.TextField()
    starts_at=models.DateTimeField()
    ends_at=models.DateTimeField()
    venue=models.CharField(max_length=240)
    address=models.CharField(max_length=400,blank=True)
    price=models.DecimalField(max_digits=8,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    payment_purpose=models.CharField(max_length=240,default='Event admission')
    booking_open=models.BooleanField(default=False)
    published=models.BooleanField(default=False)
    class Meta: ordering=['starts_at']
    def clean(self):
        if 0 < self.price < Decimal('0.30'): raise ValidationError('A paid event must cost at least £0.30.')
        if self.starts_at and self.ends_at and self.ends_at<=self.starts_at: raise ValidationError('End time must be after start time.')
    def __str__(self): return self.title
    @property
    def bookable(self): return self.published and self.booking_open and self.starts_at>timezone.now()

class Album(ImageModel):
    title=models.CharField(max_length=160)
    slug=models.SlugField(unique=True)
    event=models.ForeignKey(Event,on_delete=models.SET_NULL,blank=True,null=True)
    description=models.TextField(blank=True)
    date=models.DateField(default=timezone.localdate)
    published=models.BooleanField(default=False)
    class Meta: ordering=['-date']
    def __str__(self):return self.title

class Photo(ImageModel):
    image=models.ImageField(upload_to=image_path,validators=[validate_image])
    album=models.ForeignKey(Album,on_delete=models.CASCADE,related_name='photos')
    caption=models.CharField(max_length=300,blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    class Meta: ordering=['sort_order','id']
    def __str__(self): return self.caption or f'Photo {self.pk}'

class Video(models.Model):
    title=models.CharField(max_length=160)
    url=models.URLField(help_text='YouTube watch/share URL or Vimeo video URL.')
    description=models.TextField(blank=True)
    published=models.BooleanField(default=False)
    def clean(self):
        if not self.embed_url: raise ValidationError('Enter a valid YouTube or Vimeo video URL.')
    @property
    def embed_url(self):
        import re
        u=urlparse(self.url); host=u.hostname; key=''
        if u.scheme!='https': return ''
        if host in ('youtube.com','www.youtube.com','m.youtube.com'):
            key=parse_qs(u.query).get('v',[''])[0]
            if u.path.startswith('/shorts/'): key=u.path.split('/')[2]
        elif host=='youtu.be': key=u.path.strip('/')
        if key and re.fullmatch(r'[A-Za-z0-9_-]{11}',key):return f'https://www.youtube-nocookie.com/embed/{key}'
        if host in ('vimeo.com','www.vimeo.com') and u.path.strip('/').isdigit():return 'https://player.vimeo.com/video/'+u.path.strip('/')
        return ''
    def __str__(self):return self.title

class CommitteeMember(ImageModel):
    name=models.CharField(max_length=120)
    role=models.CharField(max_length=120)
    term=models.CharField(max_length=80,blank=True)
    bio=models.TextField(blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    published=models.BooleanField(default=False)
    class Meta: ordering=['sort_order','name']
    def __str__(self):return f'{self.name} — {self.role}'

class Resource(ImageModel):
    SECTION=[('learning','Learning Zone'),('newcomers','Newcomers Guide'),('links','Useful Links'),('community','Community Initiatives')]
    section=models.CharField(max_length=20,choices=SECTION)
    title=models.CharField(max_length=160)
    body=models.TextField()
    url=models.URLField(blank=True)
    published=models.BooleanField(default=False)
    sort_order=models.PositiveIntegerField(default=0)
    class Meta: ordering=['sort_order','title']
    def __str__(self):return self.title

class Membership(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=120)
    email=models.EmailField()
    phone=models.CharField(max_length=40,blank=True)
    area=models.CharField(max_length=120)
    household_size=models.PositiveSmallIntegerField(default=1,validators=[MinValueValidator(1),MaxValueValidator(20)])
    interests=models.TextField(blank=True,max_length=1000)
    consent=models.BooleanField(default=False)
    status=models.CharField(max_length=20,choices=[('pending','Pending review'),('approved','Approved'),('declined','Declined')],default='pending')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']
    def __str__(self):return self.name

class Enquiry(models.Model):
    name=models.CharField(max_length=120)
    email=models.EmailField()
    subject=models.CharField(max_length=160)
    message=models.TextField(max_length=5000)
    resolved=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']
    def __str__(self):return self.subject

class Order(models.Model):
    STATUS=[('pending','Awaiting payment'),('paid','Paid'),('free','Free registration'),('expired','Expired'),('failed','Payment failed'),('refunded','Refunded'),('part_refunded','Partially refunded')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    checkout_token=models.UUIDField(unique=True)
    event=models.ForeignKey(Event,on_delete=models.PROTECT,null=True,blank=True)
    membership=models.OneToOneField(Membership,on_delete=models.PROTECT,null=True,blank=True,related_name='order')
    name=models.CharField(max_length=120)
    email=models.EmailField()
    quantity=models.PositiveSmallIntegerField(default=1)
    amount_pence=models.PositiveIntegerField()
    description=models.CharField(max_length=300)
    status=models.CharField(max_length=20,choices=STATUS,default='pending')
    stripe_session=models.CharField(max_length=255,blank=True,unique=True,null=True)
    stripe_payment_intent=models.CharField(max_length=255,blank=True,db_index=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']
    @property
    def amount(self): return self.amount_pence/100
    def __str__(self):return f'{self.description} — {self.get_status_display()}'

class StripeEvent(models.Model):
    id=models.CharField(max_length=255,primary_key=True)
    created_at=models.DateTimeField(auto_now_add=True)

class RateBucket(models.Model):
    key=models.CharField(max_length=100,unique=True)
    count=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
