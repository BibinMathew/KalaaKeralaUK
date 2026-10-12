from django import forms
from .models import Membership, Enquiry
class SpamProtected(forms.Form):
    website=forms.CharField(required=False,widget=forms.HiddenInput)
    def clean_website(self):
        if self.cleaned_data['website']:raise forms.ValidationError('Unable to accept this submission.')
        return ''
class MembershipForm(SpamProtected,forms.ModelForm):
    consent=forms.BooleanField(label='I have read the privacy notice and membership terms, and agree to the club processing this application.')
    class Meta:
        model=Membership
        fields=['name','email','phone','area','household_size','interests','consent']
        widgets={'interests':forms.Textarea(attrs={'rows':3})}
class EnquiryForm(SpamProtected,forms.ModelForm):
    consent=forms.BooleanField(label='I have read the privacy notice and agree to be contacted about this enquiry.')
    class Meta:
        model=Enquiry
        fields=['name','email','subject','message']
        widgets={'message':forms.Textarea(attrs={'rows':5})}
class BookingForm(SpamProtected):
    name=forms.CharField(max_length=120)
    email=forms.EmailField()
    quantity=forms.IntegerField(min_value=1,max_value=10,initial=1)
    consent=forms.BooleanField(label='I have read the privacy notice and event cancellation / refund terms.')
