# import sys
from PIL import Image

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.safestring import mark_safe
# from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse

# from io import BytesIO

User = get_user_model()

def get_models_for_count(*model_names):
    return [models.Count(model_name) for model_name in model_names]

def get_product_url(obj, viewname):
    ct_model = obj.__class__._meta.model.__name__.lower()
    return reverse(viewname, kwargs={'ct_model': ct_model, 'slug':obj.slug})


class MinResolutionErrorException(Exception):
    pass


class MaxResolutionErrorException(Exception):
    pass


class MaxSizeException(Exception):
    pass


class LatestProductsManager:

    @staticmethod
    def get_products_for_main_page(*args, **kwargs):
        with_respect_to = kwargs.get('with_respect_to')
        products=[]
        ct_models=ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            products.extend(model_products)
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exists():
                if with_respect_to in args:
                    return sorted(
                        products, key=lambda x: x.__class__._meta.model_name.startswith(with_respect_to), reverse = True
                    )
        return products


class LatestProducts:

    objects = LatestProductsManager()


class CategoryManager(models.Manager):

    CATEGORY_NAME_COUNT_NAME = {
        'Ноутбуки':'laptop__count',
        'Телефоны':'phone__count',
    }

    def get_queryset(self):
        return super().get_queryset()

    def get_categories(self):
        models=get_models_for_count('laptop','phone')
        qs=list(self.get_queryset().annotate(*models))
        data=[
            dict(name=c.name,url=c.get_absolute_url(),count=getattr(c,self.CATEGORY_NAME_COUNT_NAME[c.name]))
            for c in qs
        ]
        return data


class Category(models.Model):

    name = models.CharField(max_length = 255, verbose_name = "Имя категории")
    slug = models.SlugField(unique = True)
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail',kwargs={'slug':self.slug})


class Product(models.Model):

    min_height = 400
    min_width = 400
    max_height = 800
    max_width = 800
    max_image_size = 3145728

    class Meta:
        abstract = True

    category = models.ForeignKey(Category, verbose_name = "Категория", on_delete = models.CASCADE)
    title = models.CharField(max_length = 255, verbose_name = "Наименование")
    slug = models.SlugField(unique = True)
    image = models.ImageField(verbose_name = "Изображение", help_text=mark_safe(
        '<span style="color:red; font-size:14px;">Загружайте изображения размером не менее 400x400 и не более 800х800'
        '<p><s>При загрузке изображения более 800 пикселей, оно будет автоматически обрезано</s></span>'
    )
                              )
    description = models.TextField(verbose_name = "Описание", null = True)
    price = models.DecimalField(max_digits = 9, decimal_places = 2, verbose_name = "Цена")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        image = self.image
        img = Image.open(image)
        if image.size > Product.max_image_size:
            raise MaxSizeException('Размер изображения должен быть не более 3 МБ')
        if img.width < self.min_width or img.height < self.min_height:
            raise MinResolutionErrorException('Разрешение изображения меньше минимального')
        if img.width > self.max_width or img.height > self.max_height:
            raise MaxResolutionErrorException('Разрешение изображения больше максимального')
        # <--- Обрезка изображений --->
        # image = self.image
        # img = Image.open(image)
        # if img.width < self.min_width or img.height < self.min_height:
        #     new_img = img.convert('RGB')
        #     resized_new_img = new_img.resize((400,400), Image.ANTIALIAS)
        #     filestream = BytesIO()
        #     resized_new_img.save(filestream, 'JPEG', quality = 90)
        #     filestream.seek(0)
        #     # name='{}.{}'.format(self.image.name.split('.'))
        #     self.image=InMemoryUploadedFile(
        #         filestream,'ImageFiled',self.image.name, 'jpeg/image', sys.getsizeof(filestream),None
        #     )
        super().save(*args,**kwargs)

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    def get_model_name(self):
        return self.__class__.__name__.lower()


class Laptop(Product):

    class Meta:
        verbose_name = "Ноутбук"
        verbose_name_plural = "Ноутбуки"

    diagonal = models.CharField(max_length=255, verbose_name="Диагональ")
    displayType = models.CharField(max_length=255, verbose_name="Тип дисплея")
    processorFreq=models.CharField(max_length=255,verbose_name="Частота процессора")
    ram = models.CharField(max_length=255, verbose_name="Оперативная память")
    video=models.CharField(max_length=255,verbose_name="Видеокарта")
    timeWithoutCharge=models.CharField(max_length=255,verbose_name="Время работы аккумулятора")

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    def __str__(self):
        return "{} : {}".format(self.category.name,self.title)


class Phone(Product):

    class Meta:
        verbose_name = "Телефон"
        verbose_name_plural = "Телефоны"

    diagonal = models.CharField(max_length=255, verbose_name="Диагональ")
    displayType = models.CharField(max_length=255, verbose_name="Тип дисплея")
    resolution = models.CharField(max_length=255, verbose_name="Разрешение экрана")
    batteryVolume = models.CharField(max_length=255, verbose_name="Объем батареи")
    ram = models.CharField(max_length=255, verbose_name="Оперативная память")
    sd = models.BooleanField(default=False, verbose_name="Наличие SD карты")
    sdVolumeMax=models.PositiveIntegerField(null=True, blank=True, verbose_name="Макс. объем встраиваемой памяти")
    mainCamera=models.CharField(max_length=255, verbose_name="Основная камера (МП)")
    frontalCamera=models.CharField(max_length=255, verbose_name="Фронтальная камера (МП)")

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    def __str__(self):
        return "{} : {}".format(self.category.name,self.title)


class CartProduct(models.Model):

    user = models.ForeignKey("Customer", verbose_name = "Покупатель", on_delete = models.CASCADE)
    cart = models.ForeignKey("Cart", verbose_name = "Корзина", on_delete = models.CASCADE, related_name="realted_products")
    content_type = models.ForeignKey(ContentType,on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    qty = models.PositiveIntegerField(default=1)
    finalPrice = models.DecimalField(max_digits = 9, decimal_places = 2, verbose_name = "Общая цена")

    def __str__(self):
        return "Продукт {} (для корзины)".format(self.content_object.title)

    def save(self, *args, **kwargs):
        self.finalPrice = self.qty * self.content_object.price
        super().save(*args, **kwargs)


class Cart(models.Model):

    owner = models.ForeignKey("Customer", verbose_name = "Владелец", null=True, on_delete = models.CASCADE)
    products = models.ManyToManyField(CartProduct, blank=True, related_name="related_cart")
    totalProducts = models.PositiveIntegerField(default=0)
    finalPrice = models.DecimalField(max_digits = 9, decimal_places = 2, verbose_name = "Общая цена", default=0)
    in_order = models.BooleanField(default=False)
    for_anonymous_user = models.BooleanField(default=False)

    def __str__(self):
        return "ID:{}".format(self.id)

    def save(self, *args, **kwargs):
        cart_data = self.products.aggregate(models.Sum('finalPrice'), models.Count('id'))
        if cart_data.get('finalPrice__sum'):
            self.finalPrice = cart_data['finalPrice__sum']
        else:
            self.finalPrice = 0
        self.totalProducts = cart_data['id__count']
        super().save(*args,**kwargs)


class Customer(models.Model):

    user = models.ForeignKey(User, verbose_name = "Пользователь", on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name="Номер телефона", null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name="Адрес", null=True, blank=True)

    def __str__(self):
        # return "Покупатель {} {}".format(self.user.firstName, self.user.lastName)
        return "Покупатель {} {}".format(self.phone, self.address)


class Specifications(models.Model):

    content_type=models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255,verbose_name="Имя товара для характеристик")

    def __str__(self):
        return "Характеристики для товара: {}".format(self.name)