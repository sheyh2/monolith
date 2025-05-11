#!/bin/bash

echo "[INFO] Установка базовых зависимостей..."
pip install -r requirements.txt

# Определим платформу
OS="$(uname)"
echo "[INFO] Обнаружена платформа: $OS"

if [[ "$OS" == "Linux" ]]; then
    echo "[INFO] Установка зависимостей для Linux..."
    pip install -r requirements-linux-only.txt
elif [[ "$OS" == "Darwin" ]]; then
    echo "[INFO] macOS обнаружен — linux-only зависимости пропущены."
else
    echo "[WARN] Неизвестная платформа — пропущены специфичные зависимости."
fi

# Флаг для установки GPU-зависимостей
if [[ "$1" == "--with-gpu" ]]; then
    echo "[INFO] Установка GPU-зависимостей..."
    pip install -r requirements-gpu.txt
else
    echo "[INFO] GPU-зависимости не установлены (используйте флаг --with-gpu)."
fi

echo "[DONE] Установка завершена."
