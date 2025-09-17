from typing import Type

from django.conf import settings
from django.db.models import Sum, F
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import ConfirmEmailToken, User, Order
from backend.tasks import send_email_task

new_user_registered = Signal()

new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    send_email_task.delay(
        subject=f"Password Reset Token for {reset_password_token.user}",
        message=reset_password_token.key,
        recipient_list=[reset_password_token.user.email]
    )


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    """
     отправляем письмо с подтрердждением почты
    """
    if created and not instance.is_active:
        # send an e-mail to the user
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)

        send_email_task.delay(
            subject=f"Password Reset Token for {instance.email}",
            message=token.key,
            recipient_list=[instance.email]
        )


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Отправляем письмо при создании нового заказа.
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)

    send_email_task.delay(
        subject=f"Обновление статуса заказа",
        message='Заказ сформирован',
        recipient_list=[user.email]
    )

    # and send email to admins
    admins = User.objects.filter(is_superuser=True)
    admin_emails = [admin.email for admin in admins]

    # Get the newly created order
    order = Order.objects.filter(user_id=user_id, state='new').latest('dt')

    # Calculate total sum
    total_sum = order.ordered_items.aggregate(total=Sum(F('quantity') * F('product_info__price')))['total']

    admin_message = f'Поступил новый заказ №{order.id} от пользователя {user.first_name} {user.last_name} ({user.email}).\n'
    admin_message += f'Сумма заказа: {total_sum}.\n'
    admin_message += 'Товары в заказе:\n'
    for item in order.ordered_items.all():
        admin_message += f'- {item.product_info.product.name} ({item.quantity} шт.)\n'

    send_email_task.delay(
        subject=f"Новый заказ №{order.id}",
        message=admin_message,
        recipient_list=admin_emails
    )
