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
    Асинхронная задача для отправки email.
    Вынесена в Celery, чтобы не блокировать основной поток выполнения
    при взаимодействии с почтовым сервером.
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
    """
    Асинхронная задача для импорта товаров из YAML-файла.
    Загружает данные по URL, обрабатывает их и обновляет каталог товаров магазина.

    Args:
        url (str): URL или путь к файлу с прайс-листом.
        shop_id (int): ID магазина, для которого выполняется импорт.
    """
    if url:
        try:
            # Проверяем, является ли URL локальным файлом, и читаем его напрямую,
            # либо загружаем по HTTP.
            if url.startswith('file://'):
                path = urlparse(url).path
                with open(path, 'rb') as f:
                    stream = f.read()
            else:
                stream = get(url).content

            data = load_yaml(stream, Loader=Loader)

            shop = Shop.objects.get(id=shop_id)

            # Обновляем или создаем категории.
            # Использование update_or_create позволяет избежать ошибок
            # при повторных импортах, обновляя существующие записи.
            for category_data in data['categories']:
                category, _ = Category.objects.update_or_create(
                    id=category_data['id'],
                    defaults={'name': category_data['name']}
                )
                category.shops.add(shop.id)
                category.save()

            # Перед импортом новых товаров, удаляем все старые товары этого магазина,
            # чтобы поддерживать каталог в актуальном состоянии.
            ProductInfo.objects.filter(shop_id=shop.id).delete()

            # Создаем новые товары и их характеристики.
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
