
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from backend.models import User, Shop, Category, Product, ProductInfo
import yaml

class APITests(APITestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(email='buyer@example.com', password='password123', type='buyer', is_active=True)
        self.shop_user = User.objects.create_user(email='shop@example.com', password='password123', type='shop', is_active=True)

        with open('/home/mladinsky/Study/python-final-diplom/data/shop1.yaml', 'r') as file:
            data = yaml.safe_load(file)

        self.shop, _ = Shop.objects.get_or_create(name=data['shop'], user=self.shop_user)
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(self.shop.id)
            category_object.save()

        for item in data['goods']:
            product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
            ProductInfo.objects.create(product_id=product.id,
                                       external_id=item['id'],
                                       model=item['model'],
                                       price=item['price'],
                                       price_rrc=item['price_rrc'],
                                       quantity=item['quantity'],
                                       shop_id=self.shop.id)

    def test_user_registration(self):
        url = reverse('backend:user-register')
        data = {
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'company': 'New Company',
            'position': 'Tester'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_user_login(self):
        url = reverse('backend:user-login')
        data = {'email': 'buyer@example.com', 'password': 'password123'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Token', response.json())

    def test_category_view(self):
        url = reverse('backend:categories')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_shop_view(self):
        url = reverse('backend:shops')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_product_info_view(self):
        url = reverse('backend:products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 14)

    def test_basket_view_unauthenticated(self):
        url = reverse('backend:basket')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_basket_view_authenticated(self):
        self.client.force_authenticate(user=self.buyer_user)
        url = reverse('backend:basket')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partner_update_unauthorized(self):
        self.client.force_authenticate(user=self.buyer_user)
        url = reverse('backend:partner-update')
        data = {'url': 'http://example.com/price.yaml'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
