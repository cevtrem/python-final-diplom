# Домашнее задание: Дипломный проект профессии «Python-разработчик: расширенный курс»

Оригинальное задание Netology: [Дипломный проект профессии «Python-разработчик: расширенный курс»](https://github.com/netology-code/python-final-diplom/blob/master/README.md)

## Описание задания

Разработка backend-приложения для автоматизации закупок в розничной сети с использованием Django Rest Framework. Сервис включает управление товарами, заказами, пользователями (клиенты и поставщики), импорт/экспорт товаров, отправку уведомлений по email, асинхронные операции и докеризацию.

## Мое решение

Проект представляет собой backend-приложение для автоматизации закупок в розничной сети, реализованное на Django Rest Framework.

**Архитектура:**
*   **Django Rest Framework:** Для создания REST API.
*   **PostgreSQL:** (предполагается, так как это стандарт для Django-проектов, хотя в `docker-compose.yml` не указан явно, но обычно используется с Django)
*   **Celery:** Для выполнения асинхронных задач (отправка email, импорт/экспорт).
*   **Redis:** Брокер сообщений для Celery.
*   **Docker, Docker Compose:** Для контейнеризации и оркестрации сервисов.

**Основные функции:**
*   **Управление пользователями:** Регистрация, авторизация, восстановление пароля для клиентов и поставщиков.
*   **Управление товарами:** Импорт товаров из YAML-файлов, возможность добавления настраиваемых полей.
*   **Управление заказами:** Создание заказов, добавление товаров от разных поставщиков в один заказ.
*   **Уведомления:** Отправка email-уведомлений администратору (накладная) и клиенту (подтверждение заказа).
*   **Асинхронные операции:** Выполнение длительных задач (импорт, отправка email) в фоновом режиме с помощью Celery.
*   **Докеризация:** Проект упакован в Docker-контейнеры для легкого развертывания.

**Используемые технологии:**
*   Python, Django, Django Rest Framework
*   Celery, Redis
*   PostgreSQL (предполагается)
*   Docker, Docker Compose
*   YAML (для импорта данных)

## Структура проекта

```
.
├── data/                       # Файлы с данными для импорта товаров (YAML)
├── reference/                  # Документация и пошаговые инструкции
│   └── netology_pd_diplom/     # Основной Django-проект
├── docker-compose.yml          # Конфигурация Docker Compose
├── Dockerfile                  # Определение Docker-образа для backend
├── requirements.txt            # Список зависимостей Python
├── .env                        # Переменные окружения
├── .gitignore                  # Файлы и папки, игнорируемые Git
├── plan.txt                    # План выполнения дипломного проекта
└── server.log                  # Лог-файл сервера
```

## Инструкции по запуску

Для запуска проекта убедитесь, что у вас установлен Docker и Docker Compose.

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/python-final-diplom.git
    cd python-final-diplom
    ```

2.  **Настройте переменные окружения:**
    Создайте файл `.env` в корневой директории проекта со следующими переменными (пример):
    ```
    SECRET_KEY=your_secret_key
    DEBUG=True
    DATABASE_URL=postgres://user:password@db:5432/dbname
    EMAIL_HOST=smtp.example.com
    EMAIL_PORT=587
    EMAIL_USE_SSL=False
    EMAIL_HOST_USER=user@example.com
    EMAIL_HOST_PASSWORD=password
    ```
    (Примечание: `DATABASE_URL` должен быть настроен в соответствии с вашей базой данных PostgreSQL. `SECRET_KEY` - это секретный ключ для Django.)

3.  **Запустите сервисы с помощью Docker Compose:**
    ```bash
    docker compose up --build
    ```

4.  **Выполните миграции базы данных:**
    После запуска контейнеров, выполните миграции в контейнере `backend`:
    ```bash
    docker compose exec backend python manage.py migrate
    ```

5.  **Создайте суперпользователя (опционально):**
    ```bash
    docker compose exec backend python manage.py createsuperuser
    ```

6.  **Доступ к API:**
    Django-приложение будет доступно по адресу `http://localhost:8000`.
    Документация API (Swagger UI) будет доступна по адресу `http://localhost:8000/swagger/` или `http://localhost:8000/redoc/`.