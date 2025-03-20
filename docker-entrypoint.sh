#!/bin/bash
set -e

# Функция для запуска API сервиса
start_api() {
    echo "Запуск API сервиса на порту 8001..."
    cd /app
    python -m src.api.main
}

# Функция для запуска DLNA сервера
start_dlna() {
    echo "Запуск DLNA сервера на порту 8080..."
    cd /app
    python -m src.dlna_stream_server.main
}

# Обработка аргументов командной строки
case "$1" in
    api)
        start_api
        ;;
    dlna)
        start_dlna
        ;;
    all)
        start_all
        ;;
    *)
        exec "$@"
        ;;
esac 