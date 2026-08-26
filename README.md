# 🚀 SyncProfile (Self-Hosted Edition)

**SyncProfile Self-Hosted** — версия плагина и полный бэкенд-сервер для самостоятельного развертывания системы синхронизации кастомных профилей Telegram (для **AyuGram** и **exteraGram**).

Плагин позволяет синхронизировать и отображать локальные параметры профиля (Telegram Premium, цвет имени и ответов, цвет обложки, анимированные эмодзи-статусы, фоновые узоры и персональные бейджи) между пользователями на вашем собственном приватном сервере.

---

## 🌟 Ключевые возможности

- 🔒 **Полный контроль над данными**: ваш собственный сервер синхронизации на базе SQLite WAL и Python.
- ⚙️ **Настраиваемый клиент**: в плагине `sync_profile.plugin` доступны поля ввода URL вашего сервера и секретного Cookie-токена.
- ⚡ **Сверхбыстрая дельта-синхронизация (`?since=...`)** с поддержкой `HTTP 304 Not Modified`.
- 🏷️ **Кастомные бейджи (`[Dev]`, `[VIP]`, `[⚡ Pro]`)** в чатах, диалогах и профиле.
- 🎨 **Официальная палитра цветов Telegram** для имени (0–20) и обложки (0–15).
- 👁️ **Интерактивный Live Preview профиля** в настройках плагина.
- 🌐 **Премиальная веб-панель управления сервером**: живой симулятор сообщений Telegram, фильтрация и экспорт бэкапов.

---

## 📁 Структура репозитория

```
SyncProfile-Selfhosted/
├── sync_profile.plugin      # Плагин для самохостинга (с полями ввода URL и Cookie)
├── sync_profile.py          # Исходный код плагина (.py)
├── build_plugin.py          # Скрипт сборки плагинов
├── zwylib.plugin            # Зависимость ZwyLib
├── server/                  # Серверная часть
│   ├── server.py            # Сервер (REST API, SQLite WAL, Web Dashboard)
│   ├── Dockerfile           # Контейнеризация
│   ├── docker-compose.yml   # Запуск через Docker Compose
│   ├── syncprofile.service  # Systemd служба для Linux
│   ├── setup_server.sh      # Автоустановка Nginx + SSL на Ubuntu/Debian
│   ├── nginx_complete.conf  # Конфигурация Nginx
│   └── requirements.txt     # Зависимости
├── tests/                   # Набор автотестов
│   └── test_server.py
└── .github/workflows/       # CI/CD автоматизация
    └── ci.yml
```

---

## 🖥️ Развертывание сервера

### Вариант 1: Через Docker Compose (Рекомендуется)
```bash
cd server
docker compose up -d
```
Сервер запустится на порту `8000`.

---

### Вариант 2: Запуск через Python напрямую
Сервер использует только стандартную библиотеку Python и не требует сторонних пакетов:
```bash
cd server
PORT=8000 HOST=0.0.0.0 python3 server.py
```

---

### Вариант 3: Автоматический скрипт для Ubuntu / Debian (с Nginx и SSL)
```bash
sudo bash server/setup_server.sh your-domain.com
```

---

## 📱 Настройка плагина в Telegram

1. Скачайте [**`sync_profile.plugin`**](https://github.com/Kukuryzen666/SyncProfile-Selfhosted/releases/latest/download/sync_profile.plugin) (и `zwylib.plugin`).
2. Отправьте файл себе в «Избранное» (Saved Messages) в Telegram и нажмите **«Установить плагин»**.
3. Перейдите в *Настройки -> Плагины -> SyncProfile*:
   - В поле **«URL сервера»** введите адрес вашего сервера (например: `https://sync.yourdomain.com`).
   - В поле **«Секретный токен Cookie»** укажите ключ доступа к серверу.
   - Настройте цвета, бейджи и нажмите **«🚀 Опубликовать профиль»**.

---

## 📡 REST API Эндпоинты

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/health` | Проверка состояния сервера и метрик |
| `GET` | `/api/profiles/updates?since=<ts>` | Дельта-синхронизация измененных профилей |
| `GET` | `/api/profiles/all` | Получение всей базы профилей (с ETag / 304) |
| `GET` | `/api/profile/{user_id}` | Получение профиля по ID |
| `POST` | `/api/profile` | Создание или обновление профиля |
| `POST` | `/api/profiles/batch` | Пакетный запрос профилей |
| `GET` | `/api/backup` | Экспорт базы данных в JSON |
| `GET` | `/` | Web Dashboard с симулятором сообщений Telegram |

---

## 🧪 Тестирование и сборка

```bash
# Запуск автотестов
python -m unittest discover tests -v

# Сборка плагина
python build_plugin.py
```

---

## 🤝 Авторы и благодарности

- **Автор проекта:** [@Kukuryzen](https://github.com/Kukuryzen666)
- **Разработка, оптимизация и аудит:** Разработано при поддержке **Antigravity AI (Google DeepMind)** в режиме парного программирования.
