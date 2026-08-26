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
python server.py
```

### 2. Запуск через Docker Compose
```bash
docker compose up -d
```

### 3. Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `PORT` | Порт сервера | `8000` |
| `HOST` | Хост сервера | `0.0.0.0` |
| `SYNC_DB_PATH` | Путь к файлу SQLite базы | `sync_profiles.db` |
| `SYNC_AUTH_KEY` | Секретный ключ (если задан, требуется `X-Auth-Key` в запросах) | *(пусто)* |

---

## 📡 REST API Спецификация

### 1. `GET /health`
Проверка состояния сервера.
```json
{
  "status": "ok",
  "service": "SyncProfile Server",
  "version": "1.0.0",
  "total_profiles": 42,
  "server_time": 1740000000,
  "server_time_iso": "2026-08-20T13:50:00Z"
}
```

### 2. `GET /api/profile/{user_id}`
Получение профиля по Telegram ID.
**Ответ:**
```json
{
  "user_id": 123456789,
  "premium": true,
  "emoji_status_id": 5310243482348572111,
  "name_color": 3,
  "name_bg_emoji_id": 5310243482348572222,
  "profile_color": 5,
  "profile_bg_emoji_id": 5310243482348572333,
  "custom_badge": "VIP User",
  "updated_at": 1740000000
}
```

### 3. `POST /api/profile`
Создание или обновление профиля.
**Запрос:**
```json
{
  "user_id": 123456789,
  "premium": true,
  "emoji_status_id": 5310243482348572111,
  "name_color": 3,
  "name_bg_emoji_id": 5310243482348572222,
  "profile_color": 5,
  "profile_bg_emoji_id": 5310243482348572333,
  "custom_badge": "VIP User",
  "auth_key": "optional_key"
}
```

### 4. `POST /api/profiles/batch`
Пакетный запрос нескольких профилей за один раз (используется для мгновенной загрузки участников чатов).
**Запрос:**
```json
{
  "user_ids": [123456789, 987654321]
}
```
**Ответ:**
```json
{
  "profiles": {
    "123456789": {
      "user_id": 123456789,
      "premium": true,
      "name_color": 3,
      ...
    }
  }
}
```

---

## 🌐 Бесплатный хостинг

Вы можете развернуть сервер в один клик на популярных сервисах:
- **Render.com**: создание Web Service -> Environment: Python -> Start Command: `python server/server.py`.
- **Railway.app**: подключение GitHub репозитория -> автоматический деплой через Dockerfile.
- **VPS (Ubuntu/Debian)**: запуск `systemd` сервиса или `docker compose up -d`.
