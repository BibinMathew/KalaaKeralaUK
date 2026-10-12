from django.contrib import admin
from django.conf import settings
from django import forms
from django.contrib import messages
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import path
from django.http import HttpResponse
import csv
from .models import *

class ClubAdminSite(admin.AdminSite):
    site_header='Kalaa Kerala · Club administration'
    site_title='Kalaa Kerala Admin'
    index_title='Events, members & community content'
    def has_permission(self,request):
        return super().has_permission(request) and request.user.is_superuser and request.user.username==settings.ADMIN_USERNAME
site=ClubAdminSite(name='clubadmin')

class PublishAdmin(admin.ModelAdmin):
    list_filter=['published']
    actions=['publish','unpublish']
    @admin.action(description='Publish selected items')
    def publish(self,request,queryset):queryset.update(published=True)
    @admin.action(description='Unpublish selected items')
    def unpublish(self,request,queryset):queryset.update(published=False)

@admin.register(SiteSettings,site=site)
class SettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self,request):return not SiteSettings.objects.exists()
    def has_delete_permission(self,request,obj=None):return False

@admin.register(Event,site=site)
class EventAdmin(PublishAdmin):
    list_display=['title','starts_at','category','price','booking_open','published']
    list_filter=['published','category','booking_open']
    prepopulated_fields={'slug':['title']}
    search_fields=['title','venue']

class PhotoInline(admin.TabularInline):
    model=Photo;extra=1

class MultipleInput(forms.ClearableFileInput):allow_multiple_selected=True
class MultipleImages(forms.FileField):
    widget=MultipleInput
    def clean(self,data,initial=None):
        files=data if isinstance(data,(list,tuple)) else [data]
        if len(files)>20:raise forms.ValidationError('Upload at most 20 images at once.')
        result=[super(MultipleImages,self).clean(f,initial) for f in files]
        for f in result:validate_image(f)
        return result
class UploadForm(forms.Form):images=MultipleImages()

@admin.register(Album,site=site)
class AlbumAdmin(PublishAdmin):
    list_display=['title','date','published']
    prepopulated_fields={'slug':['title']}
    inlines=[PhotoInline]
    change_form_template='admin/album_change.html'
    def get_urls(self):return [path('<int:pk>/upload/',self.admin_site.admin_view(self.upload),name='album_upload')]+super().get_urls()
    def upload(self,request,pk):
        album=get_object_or_404(Album,pk=pk);form=UploadForm(request.POST or None,request.FILES or None)
        if request.method=='POST' and form.is_valid():
            for f in form.cleaned_data['images']:Photo.objects.create(album=album,image=f)
            self.message_user(request,'Photos uploaded and compressed.',messages.SUCCESS)
            return redirect('clubadmin:club_album_change',pk)
        return render(request,'admin/upload.html',{**self.admin_site.each_context(request),'form':form,'album':album,'title':'Upload album photos'})

@admin.register(Photo,site=site)
class PhotoAdmin(admin.ModelAdmin):
    list_display=['__str__','album','sort_order'];list_filter=['album'];search_fields=['caption']
@admin.register(Video,site=site)
class VideoAdmin(PublishAdmin):list_display=['title','published']
@admin.register(CommitteeMember,site=site)
class CommitteeAdmin(PublishAdmin):list_display=['name','role','term','published']
@admin.register(Resource,site=site)
class ResourceAdmin(PublishAdmin):list_display=['title','section','published'];list_filter=['section','published']

def safe_csv(v):
    s=str(v)
    return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
@admin.action(description='Export selected records as CSV')
def export_csv(modeladmin,request,queryset):
    response=HttpResponse(content_type='text/csv');response['Content-Disposition']='attachment; filename="club-records.csv"'
    fields=[f for f in queryset.model._meta.fields if not f.is_relation]
    writer=csv.writer(response);writer.writerow([f.name for f in fields])
    for obj in queryset:writer.writerow([safe_csv(getattr(obj,f.name)) for f in fields])
    return response
@admin.register(Membership,site=site)
class MembershipAdmin(admin.ModelAdmin):
    list_display=['name','email','area','status','created_at'];list_filter=['status'];search_fields=['name','email'];actions=[export_csv]
    readonly_fields=['created_at','consent']
@admin.register(Enquiry,site=site)
class EnquiryAdmin(admin.ModelAdmin):
    list_display=['subject','name','resolved','created_at'];list_filter=['resolved'];readonly_fields=['created_at'];search_fields=['name','email','subject']
@admin.register(Order,site=site)
class OrderAdmin(admin.ModelAdmin):
    list_display=['id','description','email','amount','status','created_at'];list_filter=['status'];search_fields=['email','name','stripe_session'];actions=[export_csv]
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False
    def get_readonly_fields(self,request,obj=None):return [f.name for f in self.model._meta.fields]
