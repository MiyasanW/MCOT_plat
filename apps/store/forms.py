from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from allauth.account.forms import SignupForm as AllauthSignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupFormBase


class CustomAllauthSignupForm(AllauthSignupForm):
    """ฟอร์มสมัครสมาชิกของ allauth + ชื่อ นามสกุล เบอร์โทร + เงื่อนไข (ใช้กับ account_signup)"""
    field_order = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2', 'phone', 'terms_accepted']

    first_name = forms.CharField(
        required=True,
        label="ชื่อ",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'ชื่อจริง'})
    )
    last_name = forms.CharField(
        required=True,
        label="นามสกุล",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'นามสกุล'})
    )
    phone = forms.CharField(
        required=True,
        label="เบอร์โทรศัพท์",
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '0812345678'})
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label=mark_safe('ข้าพเจ้ายอมรับ <a href="#" onclick="openTOSModal(event); return false;" class="text-mcot-orange hover:underline">เงื่อนไขการใช้งาน</a>')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.field_order:
            self.order_fields(self.field_order)

    def clean_terms_accepted(self):
        if not self.cleaned_data.get('terms_accepted'):
            raise forms.ValidationError('กรุณายอมรับเงื่อนไขการใช้งาน')
        return True

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone or len(phone) < 9:
            raise forms.ValidationError('กรุณากรอกเบอร์โทรศัพท์ที่ถูกต้อง (อย่างน้อย 9 หลัก)')
        return phone

    def signup(self, request, user):
        from .models import Profile
        user.first_name = (self.cleaned_data.get('first_name') or '').strip()
        user.last_name = (self.cleaned_data.get('last_name') or '').strip()
        user.save(update_fields=['first_name', 'last_name'])
        Profile.objects.get_or_create(user=user, defaults={'phone': self.cleaned_data.get('phone', '')})


class CustomSocialSignupForm(SocialSignupFormBase):
    """ฟอร์มขั้นตอนสุดท้ายเมื่อสมัครด้วย Google — ชื่อ นามสกุล เบอร์โทร"""
    first_name = forms.CharField(
        required=True,
        label="ชื่อ",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'ชื่อจริง'})
    )
    last_name = forms.CharField(
        required=True,
        label="นามสกุล",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'นามสกุล'})
    )
    phone = forms.CharField(
        required=True,
        label="เบอร์โทรศัพท์",
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '0812345678'})
    )

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone or len(phone) < 9:
            raise forms.ValidationError('กรุณากรอกเบอร์โทรศัพท์ที่ถูกต้อง (อย่างน้อย 9 หลัก)')
        return phone


class UserRegisterForm(UserCreationForm):
    first_name = forms.CharField(
        required=True,
        label="ชื่อ",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อจริง'})
    )
    last_name = forms.CharField(
        required=True,
        label="นามสกุล",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'นามสกุล'})
    )
    email = forms.EmailField(
        required=True,
        label="อีเมล (Email)",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com'})
    )
    phone = forms.CharField(
        required=True,
        label="เบอร์โทรศัพท์ (Phone)",
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0812345678'})
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label=mark_safe('ข้าพเจ้ายอมรับ <a href="#" onclick="openTOSModal(event)" class="text-mcot-orange hover:underline">เงื่อนไขการใช้งาน</a> และยินยอมให้บริษัทฯ เก็บข้อมูลส่วนบุคคลเพื่อใช้ในการจองและบริการ'),
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 rounded border-gray-600 bg-gray-700 text-mcot-orange focus:ring-mcot-orange focus:ring-offset-gray-900',
            'style': 'accent-color: #F26522;'
        })
    )
    
    error_messages = {
        'password_mismatch': "รหัสผ่านทั้งสองช่องไม่ตรงกัน",
    }

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Username
        self.fields['username'].label = "ชื่อผู้ใช้งาน (Username)"
        self.fields['username'].help_text = "ใช้ตัวอักษรภาษาอังกฤษ, ตัวเลข และ @. + - _ เท่านั้น"
        
        # Password
        # Password
        if 'password1' in self.fields:
            self.fields['password1'].label = "รหัสผ่าน"
            self.fields['password1'].help_text = mark_safe(
                "<ul class='list-disc pl-4 mt-2 space-y-1'>"
                "<li>รหัสผ่านต้องไม่คล้ายกับข้อมูลส่วนตัวอื่นๆ ของคุณมากเกินไป</li>"
                "<li>รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร</li>"
                "<li>รหัสผ่านต้องไม่ใช่รหัสผ่านที่เดาง่ายหรือใช้กันทั่วไป</li>"
                "<li>รหัสผ่านต้องไม่เป็นตัวเลขเพียงอย่างเดียว</li>"
                "</ul>"
            )
            
        if 'password2' in self.fields:
            self.fields['password2'].label = "ยืนยันรหัสผ่าน"
            self.fields['password2'].help_text = "ใส่รหัสผ่านให้ตรงกับช่องด้านบนอีกครั้ง"

    def clean(self):
        cleaned_data = super().clean()
        accepted = cleaned_data.get('terms_accepted')
        if not accepted:
            self.add_error('terms_accepted', "กรุณายอมรับเงื่อนไขการใช้งาน")
            
        # Check email uniqueness (Django User model doesn't enforce strict unique email by default sometimes)
        email = cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
           self.add_error('email', "อีเมลนี้ถูกใช้งานแล้ว")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = (self.cleaned_data.get('first_name') or '').strip()
        user.last_name = (self.cleaned_data.get('last_name') or '').strip()
        if commit:
            user.save()
            # Explicitly create profile since post_save signal is removed
            from .models import Profile
            Profile.objects.create(user=user, phone=self.cleaned_data['phone'])
        return user
