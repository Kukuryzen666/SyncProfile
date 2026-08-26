#!/bin/bash
# ==============================================================================
# Скрипт автоматической настройки SyncProfile сервера на домене sync.efn.mom
# Подходит для Ubuntu 20.04 / 22.04 / 24.04 и Debian 11 / 12
# ==============================================================================

set -e

DOMAIN="${1:-sync.efn.mom}"
INSTALL_DIR="/opt/syncprofile"

echo "=================================================="
echo "🚀 Начало установки SyncProfile Server для $DOMAIN"
echo "=================================================="

# 1. Обновление пакетов и установка зависимостей
echo "📦 Установка Nginx, Python3 и Certbot..."
apt-get update
apt-get install -y python3 python3-pip nginx certbot python3-certbot-nginx curl

# 2. Создание рабочей директории
echo "📁 Создание каталога $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/server"

# Копирование server.py в рабочий каталог (если запущен из локальной папки)
if [ -f "server.py" ]; then
    cp server.py "$INSTALL_DIR/server/"
elif [ -f "server/server.py" ]; then
    cp server/server.py "$INSTALL_DIR/server/"
fi

# 3. Настройка Systemd службы
echo "⚙️ Настройка службы Systemd (syncprofile.service)..."
cat << 'EOF' > /etc/systemd/system/syncprofile.service
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
EOF

systemctl daemon-reload
systemctl enable syncprofile
systemctl restart syncprofile

# 4. Первичная конфигурация Nginx для выпуска SSL
echo "🌐 Настройка конфигурации Nginx..."
cat << EOF > /etc/nginx/sites-available/$DOMAIN
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Cookie \$http_cookie;
        proxy_pass_header Set-Cookie;
    }
}
EOF

ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# 5. Получение бесплатного SSL сертификата через Let's Encrypt
echo "🔒 Получение SSL сертификата для $DOMAIN..."
echo "Убедитесь, что DNS A-запись для $DOMAIN указывает на IP этого сервера!"
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect || {
    echo "⚠️ Certbot не смог автоматически выпустить сертификат. Проверьте DNS запись $DOMAIN и выполните: certbot --nginx -d $DOMAIN"
}

systemctl reload nginx

echo "=================================================="
echo "✅ Установка завершена!"
echo "🌐 Сервер доступен по адресу: https://$DOMAIN"
echo "📊 Проверить статус службы: systemctl status syncprofile"
echo "📜 Логи сервера: journalctl -u syncprofile -f"
echo "=================================================="
