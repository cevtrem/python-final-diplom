from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem,     Contact, ConfirmEmailToken, STATE_CHOICES


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'state')
    list_filter = ('state',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 0


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop', 'price', 'quantity')
    list_filter = ('shop',)
    inlines = [ProductParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ('product_info', 'parameter', 'value')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('category_name', 'price')
    fields = ('product_info', 'category_name', 'price', 'quantity')

    def category_name(self, obj):
        return obj.product_info.product.category.name
    category_name.short_description = 'Категория'

    def price(self, obj):
        return obj.product_info.price
    price.short_description = 'Цена'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'dt', 'state', 'contact')
    list_filter = ('state',)
    search_fields = ('user__email', 'id')
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        # Check if the state has changed
        if change and 'state' in form.changed_data:
            # Send email notification
            title = f'Обновление статуса заказа {obj.id}'
            message = f'Уважаемый(ая) {obj.user.first_name} {obj.user.last_name},\n\n' \
                      f'Статус вашего заказа №{obj.id} изменен на: {obj.get_state_display()}.\n\n' \
                      f'С уважением,\nВаш магазин.'
            email = obj.user.email

            msg = EmailMultiAlternatives(
                title,
                message,
                settings.EMAIL_HOST_USER,
                [email]
            )
            msg.send()
        super().save_model(request, obj, form, change)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_info', 'quantity')



@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'street', 'phone')
    search_fields = ('user__email',)


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at',)
