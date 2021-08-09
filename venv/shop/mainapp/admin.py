from PIL import Image

from django import forms
from django.contrib import admin
from django.forms import ModelChoiceField, ModelForm, ValidationError

from .models import *


class PhoneAdminForm(ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        instance=kwargs.get('instance')
        if not instance.sd:
            self.fields['sdVolumeMax'].widget.attrs.update({
                'readonly':True
            })

    def clean(self):
        if not self.cleaned_data['sd']:
            self.cleaned_data['sdVolumeMax']=None
        return self.cleaned_data



class LaptopAdminForm(ModelForm):


    def clean_image(self):
        image = self.cleaned_data['image']
        img = Image.open(image)
        if image.size > Product.max_image_size:
            raise ValidationError('Размер изображения должен быть не более 3 МБ')
        if img.width < Product.min_width or img.height < Product.min_height:
            raise ValidationError('Разрешение изображения меньше минимального')
        if img.width > Product.max_width or img.height > Product.max_height:
            raise ValidationError('Разрешение изображения больше максимального')
        return image


class LaptopAdmin(admin.ModelAdmin):

    form = LaptopAdminForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            return ModelChoiceField(Category.objects.filter(slug='laptops'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PhoneAdmin(admin.ModelAdmin):

    change_form_template = 'admin.html'
    form = PhoneAdminForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            return ModelChoiceField(Category.objects.filter(slug='phones'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Category)
admin.site.register(Laptop, LaptopAdmin)
admin.site.register(Phone, PhoneAdmin)
admin.site.register(CartProduct)
admin.site.register(Cart)
admin.site.register(Customer)