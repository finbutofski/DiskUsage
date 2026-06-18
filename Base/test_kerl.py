import os
import shutil
import subprocess
import pytest
from kerl import get_tree, count_items, get_files_sorted_by_extension


def test_count_items(tmp_path):
    """Тест быстрого подсчета элементов в папке"""
    # Создаем структуру: 2 файла и 1 подпапка (итого 3 элемента)
    sub_dir = tmp_path / "sub_folder"
    sub_dir.mkdir()
    (tmp_path / "file1.txt").write_text("hello")
    (sub_dir / "file2.jpg").write_text("world")

    total = count_items(str(tmp_path))
    assert total == 3


def test_get_tree_basic_structure(tmp_path):
    """Тест корректности построения дерева и размеров файлов"""
    # Создаем файл размером 10 байт
    file1 = tmp_path / "test_file.txt"
    file1.write_text("1234567890")  # 10 bytes

    # Создаем подпапку с файлом размером 5 байт
    sub_dir = tmp_path / "nested"
    sub_dir.mkdir()
    file2 = sub_dir / "data.dat"
    file2.write_text("abcde")  # 5 bytes

    # Запускаем наш анализатор
    tree = get_tree(str(tmp_path))

    # Проверяем структуру корня
    assert tree["type"] == "directory"
    assert tree["name"] == os.path.basename(str(tmp_path))

    # Проверяем, что размеры просуммировались корректно (10 + 5 = 15 байт)
    assert tree["size"] == 15

    # Проверяем наличие дочерних элементов
    children = tree["children"]
    assert "test_file.txt" in children
    assert "nested" in children

    # Проверяем размер отдельного файла и подпапки
    assert children["test_file.txt"]["size"] == 10
    assert children["nested"]["size"] == 5


def test_get_files_sorted_by_extension(tmp_path):
    """Тест группировки и сортировки файлов по расширениям"""
    # Создаем файлы с разными расширениями
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("12")
    (tmp_path / "c.log").write_text("123")
    (tmp_path / "no_ext").write_text("1234")

    tree = get_tree(str(tmp_path))
    ext_data = get_files_sorted_by_extension(tree)

    # Проверяем, что расширение '.txt' на первом месте, так как таких файлов больше всего (2 штуки)
    first_ext = list(ext_data.keys())[0]
    assert first_ext == ".txt"
    assert len(ext_data[".txt"]) == 2

    # Проверяем файлы без расширения
    assert "" in ext_data
    assert len(ext_data[""]) == 1


@pytest.mark.skipif(os.name != 'nt', reason="ADS поддерживается только на Windows (NTFS)")
def test_ntfs_ads_support():
    """Специальный тест для проверки интеграции NTFS ADS"""
    # Будем использовать абсолютный путь в корне проекта
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "local_test_ads_dir"))

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    try:
        file_path = os.path.join(test_dir, "ads_test.txt")

        # 1. Создаем обычный файл (5 байт)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("12345")

        # 2. Записываем ADS через cmd (команда echo запишет 5 байт '67890' БЕЗ перевода строки)
        # Флаг /p в cmd убирает лишние невидимые символы
        cmd_command = f'str/p "67890" > "{file_path}:secret"'
        # Для простоты и кросс-версионности используем классический echo (запишет 5 байт + перевод строки)
        subprocess.run(f'echo 67890> "{file_path}:secret"', shell=True, check=True)

        # Запускаем анализатор
        tree = get_tree(test_dir)
        target_file_node = tree["children"]["ads_test.txt"]

        detected_ads = target_file_node["ads_size"]
        assert detected_ads > 0
        assert target_file_node["size"] == 5 + detected_ads

    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)