# 🌐 Развертывание SyncProfile на домене sync.efn.mom

Полное пошаговое руководство по настройке сервера с поддержкой HTTPS (SSL) и Cookie-сессий.

---

## 📌 Шаг 1. Настройка DNS (A-запись)

В панели управления вашим доменом `efn.mom` (Cloudflare, Reg.ru, Namecheap и т.д.):
1. Создайте **A-запись**:
   - **Имя поддомена**: `sync` (или `sync.efn.mom`)
   - **Значение (IP)**: `IP_адрес_вашего_VPS`
   - **TTL**: Auto / 300
2. Если вы используете **Cloudflare**, на время выпуска SSL можно поставить режим DNS-only (серое облако) или оставить Full/Strict SSL.

---

## ⚡ Шаг 2. Автоматическая установка в 1 команду (Ubuntu / Debian)

Подключитесь к вашему серверу по SSH и выполните:

```bash
# 1. Создать каталог и скачать сервер
mkdir -p /opt/syncprofile/server
cd /opt/syncprofile

# 2. Загрузите файлы server.py и setup_server.sh или скопируйте их на сервер
# 3. Запустите скрипт автонастройки:
chmod +x server/setup_server.sh
sudo ./server/setup_server.sh
```

Скрипт автоматически:
- Установит Nginx, Python3 и Certbot.
- Создаст и запустит фоновую службу `syncprofile.service`.
- Настроит обратный прокси Nginx с пробросом `Cookie` и `Set-Cookie`.
- Выпустит бесплатный SSL сертификат Let's Encrypt для `sync.efn.mom`.

---

## 🛠️ Шаг 3. Ручная пошаговая настройка (Альтернатива)

Если вы хотите настроить всё вручную:

### 1. Установка пакетов
```bash
sudo apt update && sudo apt install -y python3 nginx certbot python3-certbot-nginx
```

### 2. Запуск бэкенда через Systemd
Создайте файл `/etc/systemd/system/syncprofile.service`:
```ini
[Unit]
Description=SyncProfile Server Backend (sync.efn.mom)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/syncprofile/server
ExecStart=/usr/bin/python3 /opt/syncprofile/server/server.py
Restart=always
RestartSec=3

Environment=PORT=8000
Environment=HOST=127.0.0.1
Environment=SYNC_DB_PATH=/opt/syncprofile/server/sync_profiles.db

[Install]
WantedBy=multi-user.target
```

Запустите и включите службу:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now syncprofile
```

### 3. Настройка Nginx
Создайте файл `/etc/nginx/sites-available/sync.efn.mom`:
```nginx
server {
    listen 80;
    server_name sync.efn.mom;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Проброс и сохранение Cookies
        proxy_set_header Cookie $http_cookie;
        proxy_pass_header Set-Cookie;

        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Активируйте сайт и перезапустите Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/sync.efn.mom /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Выпуск SSL сертификата (HTTPS)
```bash
sudo certbot --nginx -d sync.efn.mom
```

---

## 🍪 Как работает поддержка Cookie

1. **Сервер (`server.py`)**:
   - При публикации профиля через `POST /api/profile` сервер выставляет куку:
     `Set-Cookie: sync_session=<user_id>; Path=/; Max-Age=31536000; SameSite=Lax`
   - При открытии главной страницы `https://sync.efn.mom` в браузере сервер распознает сессионную куку и отображает статус вашего профиля.
2. **Плагин (`sync_profile.py`)**:
   - Плагин автоматически сохраняет `Set-Cookie` от сервера в локальные защищенные настройки.
   - Все последующие запросы (`POST /api/profiles/batch` и `POST /api/profile`) передают заголовок `Cookie`, сохраняя постоянную авторизованную сессию.
3. **Nginx**:
   - Параметры `proxy_set_header Cookie $http_cookie;` и `proxy_pass_header Set-Cookie;` обеспечивают беспрепятственную передачу кук между клиентом и Python-бэкендом.

---

## 🔍 Проверка работы

1. Откройте в браузере: `https://sync.efn.mom/health`
   - Должен вернуться ответ:
     ```json
     {
       "status": "ok",
       "service": "SyncProfile Server",
       "version": "1.0.0",
       "total_profiles": 0
     }
     ```
2. В приложении Telegram (AyuGram / exteraGram):
   - Откройте *Настройки -> Плагины -> SyncProfile*.
   - Убедитесь, что указан адрес `https://sync.efn.mom`.
   - Нажмите **«🔄 Проверить подключение к серверу»** -> всплывет сообщение об успешном соединении!
