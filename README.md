# 🛒 2SOUL Shop — Telegram Mini App

Магазин одежды для Telegram с админ-панелью, галереей фото, выбором ПВЗ СДЭК.

---

## ✨ Что умеет

- **Каталог** с категориями и фильтрацией
- **Карточка товара** — несколько фото с листанием и зумом, описание
- **Кнопка "Задать вопрос"** — переход в личку @twosouloff
- **Корзина** с изменением количества
- **Оформление заказа** — Telegram/VK для связи, выбор ПВЗ СДЭК
- **Админ-панель** — добавление товаров, загрузка нескольких фото, заказы

---

## 🚀 Запуск локально

### 1. Установи Python 3.9+
https://python.org/downloads

### 2. Установи зависимости
```bash
pip3 install -r requirements.txt
pip3 install werkzeug==2.3.7
```

### 3. Запусти
```bash
python3 app.py
```

### 4. Открой
- **Магазин:** http://localhost:5001
- **Админка:** http://localhost:5001/admin

**Логин:** `admin` / **Пароль:** `admin123`

---

## ☁️ Деплой (3 варианта)

### Вариант 1: Railway (рекомендую, бесплатный старт)

**Плюсы:** Очень просто, есть бесплатный лимит, автодеплой из GitHub

1. Загрузи код на GitHub
2. Зайди на https://railway.app → New Project → Deploy from GitHub
3. В настройках добавь:
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Environment:** `SECRET_KEY=твой-случайный-ключ`
4. Railway даст домен типа `xxx.up.railway.app`

**Стоимость:** $5/месяц после бесплатного лимита

---

### Вариант 2: Render (бесплатный)

**Плюсы:** Полностью бесплатно, просто

**Минусы:** Сервер "засыпает" после 15 мин неактивности (просыпается ~30 сек)

1. Зайди на https://render.com
2. New → Web Service → Connect GitHub
3. Settings:
   - **Build Command:** `pip install -r requirements.txt && pip install werkzeug==2.3.7`
   - **Start Command:** `gunicorn app:app`
4. Получишь домен `xxx.onrender.com`

---

### Вариант 3: VPS (полный контроль)

**Плюсы:** Полный контроль, можно много всего

**Минусы:** Нужны базовые навыки Linux

**Рекомендую:** Timeweb Cloud, Selectel, DigitalOcean (~500-1000₽/мес)

```bash
# На сервере Ubuntu 22.04

# Установка
sudo apt update
sudo apt install python3 python3-pip nginx certbot python3-certbot-nginx

# Клонируй проект
git clone https://github.com/твой-юзер/2soul-shop.git
cd 2soul-shop

# Установи зависимости
pip3 install -r requirements.txt
pip3 install werkzeug==2.3.7

# Создай systemd сервис
sudo nano /etc/systemd/system/2soul.service
```

Содержимое файла:
```ini
[Unit]
Description=2SOUL Shop
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/твой-юзер/2soul-shop
ExecStart=/usr/bin/gunicorn app:app -w 2 -b 127.0.0.1:5001
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Запусти
sudo systemctl enable 2soul
sudo systemctl start 2soul

# Настрой Nginx
sudo nano /etc/nginx/sites-available/2soul
```

Nginx конфиг:
```nginx
server {
    listen 80;
    server_name твой-домен.ru;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /home/твой-юзер/2soul-shop/static;
    }

    client_max_body_size 32M;
}
```

```bash
# Активируй
sudo ln -s /etc/nginx/sites-available/2soul /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL сертификат (бесплатно)
sudo certbot --nginx -d твой-домен.ru
```

---

## 🤖 Подключение к Telegram

### 1. Создай бота
1. Открой @BotFather
2. `/newbot` → придумай имя
3. Сохрани токен

### 2. Подключи Mini App

Вариант А — **Кнопка меню:**
```
/mybots → выбери бота → Bot Settings → Menu Button → Configure
URL: https://твой-домен.ru
Button text: 🛒 Магазин
```

Вариант Б — **Web App кнопка в чате:**
```
/mybots → выбери бота → Bot Settings → Menu Button → Edit Web App URL
```

### 3. Готово!
Теперь в боте появится кнопка, открывающая магазин.

---

## ⚙️ Настройка

### Изменить контакт для вопросов
В файле `static/index.html` найди:
```javascript
const CONTACT_TG = '@twosouloff';
```
Замени на свой username.

### Изменить название
В `static/index.html`:
```html
<div class="logo">2SOUL</div>
```

### СДЭК интеграция
Сейчас пункты выдачи — демо-данные. Для реальной интеграции:
1. Зарегистрируйся на https://www.cdek.ru/ru/integration/api
2. Получи API-ключи
3. Добавь загрузку реальных ПВЗ через их API

---

## 📱 Важно: мобильная оптимизация

Приложение уже оптимизировано:
- Touch-события для свайпа галереи
- Правильные viewport meta-теги
- Отключение zoom на инпутах
- Адаптивная сетка
- Haptic feedback на устройствах

---

## 🔐 Безопасность

**Обязательно после деплоя:**

1. Смени пароль админа: Админка → Настройки
2. Измени `secret_key` в `app.py`
3. Используй HTTPS (Railway/Render дают автоматически)

---

## 📂 Структура проекта

```
2soul-shop/
├── app.py              # Сервер Flask
├── requirements.txt    # Зависимости
├── shop.db            # База данных (создаётся автоматически)
├── static/
│   ├── index.html     # Фронтенд магазина
│   └── uploads/       # Фото товаров
└── templates/
    ├── admin_*.html   # Шаблоны админки
```

---

## ❓ Проблемы и решения

**"python: command not found"**
→ Используй `python3` вместо `python`

**"Port 5000 in use"**
→ Уже исправлено, используется порт 5001

**Фото не загружаются**
→ Проверь права на папку `static/uploads`

**Заказы не видны**
→ Они сохраняются в базу, смотри в Админка → Заказы

---

## 💡 Что можно улучшить

- [ ] Реальная интеграция СДЭК API
- [ ] Уведомления в Telegram бот о новых заказах
- [ ] Онлайн-оплата (ЮKassa)
- [ ] Админка для редактирования описания бренда
- [ ] Push-уведомления

Если нужна помощь с чем-то из этого — спрашивай!
