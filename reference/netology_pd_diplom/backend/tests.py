from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from backend.models import User, Shop, Category, Product, ProductInfo, ConfirmEmailToken
import yaml
from django.db import transaction
import json


class APITests(APITestCase):


    def setUp(self):

        """Настраивает тестовые данные для всех тестов."""

        self.buyer_user = User.objects.create_user(email='buyer@example.com', password='password123', type='buyer')
        self.shop_user = User.objects.create_user(email='shop@example.com', password='password123', type='shop')

        with open('/home/mladinsky/Study/python-final-diplom/data/shop1.yaml', 'r') as file:
            data = yaml.safe_load(file)

        self.shop, _ = Shop.objects.get_or_create(name=data['shop'], user=self.shop_user)
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(self.shop.id)
            category_object.save()
            if not hasattr(self, 'category'): # Assign the first category to self.category
                self.category = category_object

        for item in data['goods']:
            product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
            product_info_object = ProductInfo.objects.create(product_id=product.id,
                                       external_id=item['id'],
                                       model=item['model'],
                                       price=item['price'],
                                       price_rrc=item['price_rrc'],
                                       quantity=item['quantity'],
                                       shop_id=self.shop.id)
            if not hasattr(self, 'product_info'):
                self.product_info = product_info_object

        # Create a second shop and product for testing multiple shops in basket
        self.shop2_user = User.objects.create_user(email='shop2@example.com', password='password123', type='shop')
        self.shop2, _ = Shop.objects.get_or_create(name='Test Shop 2', user=self.shop2_user)
        self.product2 = Product.objects.create(name='Test Product 2', category=self.category)
        self.product_info2 = ProductInfo.objects.create(product=self.product2, shop=self.shop2, price=200, quantity=5, external_id=2, price_rrc=220)


    def test_user_registration(self):

        """Проверяет успешную регистрацию нового пользователя."""

        url = reverse('backend:user-register')
        data = {
            'email': 'newuser@example.com',
            'password': 'StrongPassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'company': 'New Company',
            'position': 'Tester'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())


    def test_user_login(self):

        """Проверяет авторизацию пользователя после регистрации и подтверждения."""

        # First, register a new user
        register_url = reverse('backend:user-register')
        user_data = {
            'email': 'testlogin@example.com',
            'password': 'StrongPassword123!',
            'first_name': 'Test',
            'last_name': 'Login',
            'company': 'Test Company',
            'position': 'Tester'
        }
        self.client.post(register_url, user_data, format='json')

        # Get the confirmation token
        user = User.objects.get(email='testlogin@example.com')
        token = ConfirmEmailToken.objects.get(user=user)

        # Confirm the account using the token
        confirm_url = reverse('backend:user-register-confirm')
        confirm_data = {
            'email': 'testlogin@example.com',
            'token': token.key
        }
        self.client.post(confirm_url, confirm_data, format='json')

        # Now, try to log in
        login_url = reverse('backend:user-login')
        login_data = {'email': 'testlogin@example.com', 'password': 'StrongPassword123!'}
        response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Token', response.json())


    def test_category_view(self):

        """Проверяет получение списка категорий."""

        url = reverse('backend:categories')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)


    def test_shop_view(self):

        """Проверяет получение списка магазинов."""

        url = reverse('backend:shops')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)


    def test_product_info_view(self):

        """Проверяет получение информации о продуктах."""

        url = reverse('backend:products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 15)


    def test_basket_view_unauthenticated(self):

        """Проверяет доступ к корзине для неавторизованного пользователя."""

        url = reverse('backend:basket')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_basket_view_authenticated(self):

        """Проверяет доступ к корзине для авторизованного пользователя."""

        self.client.force_authenticate(user=self.buyer_user)
        url = reverse('backend:basket')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_partner_update_unauthorized(self):

        """Проверяет доступ к обновлению прайс-листа для неавторизованного пользователя."""

        self.client.force_authenticate(user=self.buyer_user)
        url = reverse('backend:partner-update')
        data = {'url': 'http://example.com/price.yaml'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_add_multiple_items_to_basket_from_different_shops(self):

        """Проверяет добавление нескольких товаров из разных магазинов в корзину."""

        self.client.force_authenticate(user=self.buyer_user)
        url = reverse('backend:basket')
        items_data = [
            {'product_info': self.product_info.id, 'quantity': 1},
            {'product_info': self.product_info2.id, 'quantity': 2},
        ]
        response = self.client.post(url, {'items': json.dumps(items_data)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['Status'])
        self.assertEqual(response.json()['Создано объектов'], 2)

        # Verify items are in basket
        basket_response = self.client.get(url)
        self.assertEqual(basket_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(basket_response.json()[0]['ordered_items']), 2)