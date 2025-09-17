from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from yaml import load as load_yaml, Loader
from requests import get
from urllib.parse import urlparse
from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter


@shared_task
def send_email_task(subject, message, recipient_list):
    """
    A task to send an email.
    """
    msg = EmailMultiAlternatives(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        recipient_list
    )
    msg.send()


@shared_task
def do_import(url, shop_id):
    if url:
        try:
            if url.startswith('file://'):
                path = urlparse(url).path
                with open(path, 'rb') as f:
                    stream = f.read()
            else:
                stream = get(url).content
            
            data = load_yaml(stream, Loader=Loader)

            shop = Shop.objects.get(id=shop_id)

            for category_data in data['categories']:
                category, _ = Category.objects.update_or_create(
                    id=category_data['id'], 
                    defaults={'name': category_data['name']}
                )
                category.shops.add(shop.id)
                category.save()

            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          external_id=item['id'],
                                                          model=item['model'],
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter_object.id,
                                                    value=value)

            return {'Status': True}
        except Exception as e:
            return {'Status': False, 'Error': str(e)}
    return {'Status': False, 'Errors': 'No URL provided'}
