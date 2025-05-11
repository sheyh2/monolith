.PHONY: install

# Устанавливаем пакет и добавляем его в requirements
install:
	@echo "Установка пакета $(package)"
	pip install $(package)
	python add_package.py $(package)

# Устанавливаем все зависимости из requirements.txt
install-all:
	@echo "Установка всех зависимостей из requirements.txt"
	pip install -r requirements.txt

install-gpu:
	@echo "Установка всех GPU зависимостей из requirements-gpu.txt"
	pip install -r requirements-gpu.txt

install-linux-only:
	@echo "Установка всех зависимостей для Linux из requirements-linux-only.txt"
	pip install -r requirements-linux-only.txt
