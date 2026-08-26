# 🖥️ SyncProfile Server Backend

Легковесный и быстрый сервер синхронизации профилей для плагина **SyncProfile** (AyuGram / exteraGram).

---

## 📋 Требования
- Python 3.8+ (работает из коробки на стандартной библиотеке)
- Либо Docker / Docker Compose

---

## ⚡ Способы запуска

### 1. Автономный запуск (Python)
Сервер не требует установки дополнительных библиотек и использует только стандартные модули Python (`sqlite3`, `http.server`, `json`):

```bash
PORT=8000 python3 server.py
```

### 2. Запуск через Docker Compose
```bash
docker compose up -d
```

### 3. Автоустановка на Ubuntu / Debian с Nginx и SSL
```bash
sudo bash setup_server.sh your-domain.com
```

### 4. Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `PORT` | Порт сервера | `8000` |
| `HOST` | Хост сервера | `0.0.0.0` |
| `SYNC_DB_PATH` | Путь к файлу SQLite базы | `sync_profiles.db` |
| `SYNC_AUTH_KEY` | Секретный ключ (если задан, требуется `X-Auth-Key` в запросах) | *(пусто)* |

---

## 📡 REST API Спецификация

### 1. `GET /`
Страница статуса сервиса (Service Status).

### 2. `GET /health`
Проверка состояния сервера в формате JSON.
```json
{
  "status": "ok",
  "service": "SyncProfile Server",
  "version": "10.1.5",
  "total_profiles": 42,
  "server_time": 1740000000,
  "server_time_iso": "2026-08-20T13:50:00Z"
}
```

### 3. `GET /api/profiles/updates?since={timestamp}`
Дельта-синхронизация измененных профилей.

### 4. `GET /api/profile/{user_id}`
Получение профиля по Telegram ID.
```json
{
  "user_id": 123456789,
  "premium": true,
  "emoji_status_id": 5310243482348572111,
  "name_color": 3,
  "name_bg_emoji_id": 5310243482348572222,
  "profile_color": 5,
  "profile_bg_emoji_id": 5310243482348572333,
  "updated_at": 1740000000
}
```

### 5. `POST /api/profile`
Создание или обновление профиля.
```json
{
  "user_id": 123456789,
  "premium": true,
  "emoji_status_id": 5310243482348572111,
  "name_color": 3,
  "name_bg_emoji_id": 5310243482348572222,
  "profile_color": 5,
  "profile_bg_emoji_id": 5310243482348572333,
  "auth_key": "optional_key"
}
```

### 6. `POST /api/profiles/batch`
Пакетный запрос нескольких профилей.
```json
{
  "user_ids": [123456789, 987654321]
}
```
