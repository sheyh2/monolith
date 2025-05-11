import sys
import pkg_resources

# Список ключевых слов для GPU и Linux зависимостей
gpu_keywords = ["nvidia", "cudnn", "onnxruntime-gpu", "mxnet-cu"]
linux_only_keywords = ["dlib", "lap", "uvloop", "Cython"]


def add_package_to_requirements(package_name):
    # Получаем информацию о пакете
    dist = pkg_resources.get_distribution(package_name)
    req = f"{dist.project_name}=={dist.version}"

    # Определяем, куда добавить пакет
    if any(kw in dist.project_name.lower() for kw in gpu_keywords):
        filename = 'requirements-gpu.txt'
    elif any(kw in dist.project_name.lower() for kw in linux_only_keywords):
        filename = 'requirements-linux-only.txt'
    else:
        filename = 'requirements.txt'

    # Добавляем в соответствующий файл
    with open(filename, 'a') as f:
        f.write(f"{req}\n")
    print(f"[INFO] Пакет {package_name} добавлен в {filename}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python add_package.py <package-name>")
    else:
        add_package_to_requirements(sys.argv[1])
