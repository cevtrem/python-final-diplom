from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from backend.models import User, Shop, Category, Product, ProductInfo, ConfirmEmailToken, Contact, Order
import yaml
import json
from unittest.mock import patch, Mock


class APITests(APITestCase):

    def setUp(self):
        """Настраивает тестовые данные для всех тестов."""
        self.buyer_user = User.objects.create_user(email='buyer@example.com', password='password123', type='buyer')
        self.shop_user = User.objects.create_user(email='shop@example.com', password='password123', type='shop')
        self.admin_user = User.objects.create_superuser(email='admin@example.com', password='adminpassword')

        with open('../../data/shop1.yaml', 'r') as file:
            data = yaml.safe_load(file)

        self.shop, _ = Shop.objects.get_or_create(name=data['shop'], user=self.shop_user)
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(self.shop.id)
            category_object.save()
            if not hasattr(self, 'category'):  # Assign the first category to self.category
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

    def test_confirm_order_with_address(self):
        """Проверяет подтверждение заказа с вводом адреса доставки."""
        self.client.force_authenticate(user=self.buyer_user)
        # 1. Add a contact
        contact_url = reverse('backend:user-contact')
        contact_data = {
            'city': 'Москва',
            'street': 'Ленина',
            'phone': '+79001234567',
            'house': '10',
            'apartment': '5',
        }
        contact_response = self.client.post(contact_url, contact_data, format='json')
        self.assertEqual(contact_response.status_code, status.HTTP_200_OK)
        self.assertTrue(contact_response.json()['Status'])

        # Get the contact ID
        contacts_list_response = self.client.get(contact_url)
        contact_id = contacts_list_response.json()[0]['id']

        # 2. Add items to basket
        basket_url = reverse('backend:basket')
        items_data = [
            {'product_info': self.product_info.id, 'quantity': 1},
        ]
        basket_add_response = self.client.post(basket_url, {'items': json.dumps(items_data)}, format='json')
        self.assertEqual(basket_add_response.status_code, status.HTTP_200_OK)
        self.assertTrue(basket_add_response.json()['Status'])

        # Get the basket ID
        basket_get_response = self.client.get(basket_url)
        basket_id = basket_get_response.json()[0]['id']

        # 3. Confirm the order
        order_url = reverse('backend:order')
        order_confirm_data = {
            'id': basket_id,
            'contact': contact_id,
        }
        order_confirm_response = self.client.post(order_url, order_confirm_data, format='json')
        self.assertEqual(order_confirm_response.status_code, status.HTTP_200_OK)
        self.assertTrue(order_confirm_response.json()['Status'])

        # Verify order status is 'new'
        orders_list_response = self.client.get(order_url)
        self.assertEqual(orders_list_response.json()[0]['state'], 'new')

    def test_view_created_orders(self):
        """Проверяет просмотр созданных заказов."""
        self.client.force_authenticate(user=self.buyer_user)
        # Create an order first (reusing logic from test_confirm_order_with_address)
        contact_url = reverse('backend:user-contact')
        contact_data = {
            'city': 'Москва',
            'street': 'Ленина',
            'phone': '+79001234567',
            'house': '10',
            'apartment': '5',
        }
        self.client.post(contact_url, contact_data, format='json')
        contacts_list_response = self.client.get(contact_url)
        contact_id = contacts_list_response.json()[0]['id']

        basket_url = reverse('backend:basket')
        items_data = [
            {'product_info': self.product_info.id, 'quantity': 1},
        ]
        self.client.post(basket_url, {'items': json.dumps(items_data)}, format='json')
        basket_get_response = self.client.get(basket_url)
        basket_id = basket_get_response.json()[0]['id']

        order_url = reverse('backend:order')
        order_confirm_data = {
            'id': basket_id,
            'contact': contact_id,
        }
        self.client.post(order_url, order_confirm_data, format='json')

        # Now, view the created orders
        view_orders_response = self.client.get(order_url)
        self.assertEqual(view_orders_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(view_orders_response.json()), 1)  # Expecting one order
        self.assertEqual(view_orders_response.json()[0]['state'], 'new')

    @patch('backend.tasks.EmailMultiAlternatives')
    def test_new_order_email_sent(self, mock_email):
        """Проверяет, что при создании нового заказа отправляется email."""
        self.client.force_authenticate(user=self.buyer_user)
        # 1. Add a contact
        contact_url = reverse('backend:user-contact')
        contact_data = {
            'city': 'Test City',
            'street': 'Test Street',
            'phone': '+79998887766',
            'house': '1',
        }
        self.client.post(contact_url, contact_data, format='json')
        contacts_list_response = self.client.get(contact_url)
        contact_id = contacts_list_response.json()[0]['id']

        # 2. Add items to basket
        basket_url = reverse('backend:basket')
        items_data = [{'product_info': self.product_info.id, 'quantity': 5}]
        self.client.post(basket_url, {'items': json.dumps(items_data)}, format='json')
        basket_get_response = self.client.get(basket_url)
        basket_id = basket_get_response.json()[0]['id']

        # 3. Confirm the order
        order_url = reverse('backend:order')
        order_confirm_data = {
            'id': basket_id,
            'contact': contact_id,
        }
        self.client.post(order_url, order_confirm_data, format='json')

        # 4. Assert that the email was sent
        self.assertEqual(mock_email.call_count, 2)

        # Check user email
        user_email_call = mock_email.call_args_list[0]
        args, kwargs = user_email_call
        self.assertEqual(args[0], 'Обновление статуса заказа')  # subject
        self.assertEqual(args[3], [self.buyer_user.email])

        # Check admin email
        admin_email_call = mock_email.call_args_list[1]
        args, kwargs = admin_email_call
        self.assertIn('Новый заказ', args[0])  # Subject
        self.assertIn('Поступил новый заказ', args[1])  # Body
        self.assertEqual(args[3], [self.admin_user.email])

    @patch('backend.views.get')
    def test_partner_update_authorized(self, mock_get):
        """Проверяет успешное обновление прайс-листа авторизованным магазином."""
        # Create a new shop user for this test to avoid conflicts with setUp
        new_shop_user = User.objects.create_user(email='newshop@example.com', password='password123', type='shop')

        # Mock the response from requests.get
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
shop: New Test Shop
categories:
- id: 99999
  name: New Category
goods:
- id: 101
  category: 99999
  model: New Model S
  name: New Product 1
  price: 150.50
  price_rrc: 160.00
  quantity: 10
  parameters:
    param1: value1
    param2: value2
"""
        mock_get.return_value = mock_response

        self.client.force_authenticate(user=new_shop_user)
        url = reverse('backend:partner-update')
        data = {'url': 'http://example.com/new_price.yaml'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['Status'])

        # Verify that the new product is in the database
        self.assertTrue(ProductInfo.objects.filter(
            shop__user=new_shop_user,
            product__name='New Product 1',
            model='New Model S'
        ).exists())

    @patch('backend.tasks.EmailMultiAlternatives')
    def test_admin_order_status_change_sends_email(self, mock_email):
        """Проверяет, что при изменении статуса заказа в админке отправляется email."""
        # Create an order for a buyer user
        buyer_user = User.objects.create_user(email='admin_test_buyer@example.com', password='password123', type='buyer', first_name="Test", last_name="Buyer")
        contact = Contact.objects.create(user=buyer_user, city='OrderTestCity', street='OrderTestStreet', phone='+9876543210')
        order = Order.objects.create(user=buyer_user, state='new', contact=contact)

        # Log in as a superuser (admin)
        self.client.force_login(self.admin_user)

        # Change the order status in the admin
        change_url = reverse('admin:backend_order_change', args=[order.id])

        # Data for the POST request, mimicking a real admin form submission
        post_data = {
            'user': order.user.id,
            'dt_0': order.dt.strftime('%Y-%m-%d'),  # Date part
            'dt_1': order.dt.strftime('%H:%M:%S'),  # Time part
            'state': 'confirmed',
            'contact': order.contact.id,
            'ordered_items-TOTAL_FORMS': 0,
            'ordered_items-INITIAL_FORMS': 0,
            'ordered_items-MIN_NUM_FORMS': 0,
            'ordered_items-MAX_NUM_FORMS': 1000,
            '_save': 'Save',  # This is crucial to trigger the save action
        }

        response = self.client.post(change_url, post_data, follow=True)

        self.assertEqual(response.status_code, 200)
        # Check that we are on the changelist page and a success message is displayed
        self.assertContains(response, 'was changed successfully.')

        # Refresh the order from the database to check its new state
        order.refresh_from_db()
        self.assertEqual(order.state, 'confirmed')

        # Check that the email was sent
        self.assertEqual(mock_email.call_count, 2)

        # Check email content
        args, kwargs = mock_email.call_args
        self.assertEqual(args[0], f'Обновление статуса заказа {order.id}')  # Subject
        self.assertIn(f'Статус вашего заказа №{order.id} изменен на: Подтвержден.', args[1])  # Body
        self.assertEqual(args[3], [buyer_user.email])  # To
