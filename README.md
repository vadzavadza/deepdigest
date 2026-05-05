# DeepDigest — Backend

FastAPI backend для новостного Telegram-канала с ИИ.

## Стек
- **FastAPI** — API
- **PostgreSQL** — база данных (через Railway)
- **SQLAlchemy async** — ORM
- **Resend** — отправка email
- **Railway** — деплой

---

## Локальный запуск

### 1. Клонируй репо и установи зависимости
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настрой .env
```bash
cp .env.example .env
```
Заполни в `.env`:
- `SECRET_KEY` → запусти: `openssl rand -hex 32`
- `DATABASE_URL` → строка подключения к PostgreSQL
- `RESEND_API_KEY` → получи на [resend.com](https://resend.com) (бесплатно)
- `TELEGRAM_BOT_TOKEN` → токен твоего бота

### 3. Создай базу данных
```bash
# Создай БД в PostgreSQL, потом:
alembic upgrade head
```

### 4. Запусти
```bash
uvicorn app.main:app --reload
```
Открой: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

---

## Деплой на Railway

### 1. Создай аккаунт на [railway.app](https://railway.app)

### 2. Создай проект
```bash
# Установи Railway CLI:
npm install -g @railway/cli

railway login
railway init
railway up
```

### 3. Добавь PostgreSQL
В Railway Dashboard → Add Service → PostgreSQL  
Скопируй `DATABASE_URL` и добавь в Variables.

### 4. Добавь переменные окружения
В Railway Dashboard → Variables — добавь все из `.env.example`

### 5. Готово 🚀
Railway автоматически задеплоит при каждом `git push`

---

## API endpoints

| Method | URL | Описание |
|--------|-----|----------|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/login` | Логин → JWT токен |
| GET  | `/api/auth/verify?token=...` | Подтверждение email |
| POST | `/api/auth/forgot-password` | Запрос сброса пароля |
| POST | `/api/auth/reset-password` | Сброс пароля |
| GET  | `/api/users/me` | Профиль текущего юзера |
| PATCH| `/api/users/me` | Обновить профиль |
| GET  | `/api/digest/latest` | Последний дайджест |

---

## Статистика сайта (Umami)

Добавь в `static/index.html` перед `</head>`:
```html
<script async src="https://analytics.umami.is/script.js"
        data-website-id="ВАШ-ID"></script>
```
Зарегистрируйся на [umami.is](https://umami.is) — бесплатно.

---

## Структура проекта
```
deepdigest/
├── app/
│   ├── api/
│   │   ├── deps.py          # JWT зависимости
│   │   └── routes/
│   │       ├── auth.py      # Регистрация, логин, верификация
│   │       ├── users.py     # Профиль юзера
│   │       └── digest.py    # Дайджесты (подключи свой бот)
│   ├── core/
│   │   ├── config.py        # Все настройки из .env
│   │   └── security.py      # JWT, хэширование паролей
│   ├── db/
│   │   ├── base.py          # SQLAlchemy Base
│   │   └── session.py       # Async сессия
│   ├── models/
│   │   └── user.py          # Модель пользователя
│   ├── schemas/
│   │   └── auth.py          # Pydantic схемы
│   ├── services/
│   │   ├── email.py         # Отправка писем (Resend)
│   │   └── notifications.py # Telegram уведомления
│   └── main.py              # Точка входа
├── alembic/                 # Миграции БД
├── static/
│   └── index.html           # Лендинг (раздаётся FastAPI)
├── .env.example
├── Dockerfile
├── railway.toml
└── requirements.txt
```
