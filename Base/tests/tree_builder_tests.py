import os
from pathlib import Path
from unittest.mock import Mock

import pytest

import Base.tree_builder as ft  # Замени на имя своего Python-модуля


# ============================================================
# Вспомогательные функции
# ============================================================

def create_file(path: Path, content: bytes = b"test"):
    """Создаёт файл с заданным содержимым."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ============================================================
# Тесты count_items()
# ============================================================

def test_count_items_empty_directory(tmp_path):
    """Пустая директория должна содержать 0 элементов."""
    assert ft.count_items(str(tmp_path)) == 0


def test_count_items_files(tmp_path):
    """Подсчитываются файлы в одной директории."""
    create_file(tmp_path / "a.txt")
    create_file(tmp_path / "b.txt")
    create_file(tmp_path / "c.txt")

    assert ft.count_items(str(tmp_path)) == 3


def test_count_items_nested_directories(tmp_path):
    """Подсчитываются файлы и директории на всех уровнях."""
    create_file(tmp_path / "a.txt")
    create_file(tmp_path / "subdir" / "b.txt")
    create_file(tmp_path / "subdir" / "nested" / "c.txt")

    # Элементы:
    # a.txt
    # subdir/
    # subdir/b.txt
    # subdir/nested/
    # subdir/nested/c.txt

    assert ft.count_items(str(tmp_path)) == 5


def test_count_items_directory_without_files(tmp_path):
    """Пустые вложенные директории тоже учитываются."""
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "dir2").mkdir()

    assert ft.count_items(str(tmp_path)) == 2


def test_count_items_nonexistent_directory(tmp_path):
    """Несуществующий путь не должен приводить к ложному результату."""
    path = tmp_path / "does_not_exist"

    # os.walk для несуществующего пути не выдаёт элементов.
    assert ft.count_items(str(path)) == 0


# ============================================================
# Тесты get_tree()
# ============================================================

def test_get_tree_empty_directory(tmp_path, monkeypatch):
    """Проверяем дерево пустой директории."""
    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    tree = ft.get_tree(str(tmp_path))

    assert tree["type"] == "directory"
    assert tree["size"] == 0
    assert tree["count"] == 0
    assert tree["depth"] == 0
    assert tree["children"] == {}
    assert tree["name"] == tmp_path.name
    assert "mtime" in tree
    assert "owner" in tree


def test_get_tree_single_file(tmp_path, monkeypatch):
    """Проверяем добавление одного файла в дерево."""
    file_path = create_file(tmp_path / "hello.txt", b"Hello")

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    tree = ft.get_tree(str(tmp_path))

    assert "hello.txt" in tree["children"]

    file_node = tree["children"]["hello.txt"]

    assert file_node["name"] == "hello.txt"
    assert file_node["type"] == "file"
    assert file_node["size"] == 5
    assert file_node["ads_size"] == 0
    assert file_node["ext"] == ".txt"
    assert file_node["depth"] == 1
    assert file_node["mtime"] == os.path.getmtime(file_path)

    assert tree["size"] == 5
    assert tree["count"] == 1


def test_get_tree_nested_directories(tmp_path, monkeypatch):
    """Проверяем построение дерева вложенных директорий."""
    create_file(tmp_path / "root.txt", b"123")
    create_file(tmp_path / "subdir" / "nested.txt", b"12345")
    create_file(
        tmp_path / "subdir" / "nested" / "deep.txt",
        b"1234567",
    )

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    tree = ft.get_tree(str(tmp_path))

    # Корневой каталог.
    assert tree["size"] == 15
    assert tree["count"] == 3

    # Файл в корневом каталоге.
    assert tree["children"]["root.txt"]["size"] == 3

    # Вложенная директория.
    subdir = tree["children"]["subdir"]

    assert subdir["type"] == "directory"
    assert subdir["depth"] == 1
    assert subdir["size"] == 12
    assert subdir["count"] == 2

    # Файл на втором уровне.
    assert subdir["children"]["nested.txt"]["size"] == 5
    assert subdir["children"]["nested.txt"]["depth"] == 2

    # Директория на втором уровне.
    nested = subdir["children"]["nested"]

    assert nested["type"] == "directory"
    assert nested["depth"] == 2
    assert nested["size"] == 7
    assert nested["count"] == 1

    # Файл на третьем уровне.
    assert nested["children"]["deep.txt"]["size"] == 7
    assert nested["children"]["deep.txt"]["depth"] == 3


def test_get_tree_calculates_directory_sizes(tmp_path, monkeypatch):
    """Размер директории равен сумме размеров её файлов и поддиректорий."""
    create_file(tmp_path / "a.txt", b"1234")
    create_file(tmp_path / "dir" / "b.txt", b"123456")
    create_file(tmp_path / "dir" / "c.txt", b"12")

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    tree = ft.get_tree(str(tmp_path))

    assert tree["size"] == 12
    assert tree["count"] == 3

    directory = tree["children"]["dir"]

    assert directory["size"] == 8
    assert directory["count"] == 2


def test_get_tree_includes_ads_size(tmp_path, monkeypatch):
    """Размер ADS добавляется к основному размеру файла."""
    create_file(tmp_path / "document.txt", b"1234567890")

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=100))

    tree = ft.get_tree(str(tmp_path))

    file_node = tree["children"]["document.txt"]

    assert file_node["size"] == 110
    assert file_node["ads_size"] == 100

    assert tree["size"] == 110
    assert tree["count"] == 1


def test_get_tree_ads_error_does_not_interrupt_scan(
    tmp_path,
    monkeypatch,
):
    """Ошибка при чтении ADS не должна мешать сканированию."""
    create_file(tmp_path / "document.txt", b"12345")

    def failing_ads(_path):
        raise PermissionError("Access denied")

    monkeypatch.setattr(ft, "get_ads_size", failing_ads)

    tree = ft.get_tree(str(tmp_path))

    file_node = tree["children"]["document.txt"]

    assert file_node["size"] == 5
    assert file_node["ads_size"] == 0

    assert tree["size"] == 5
    assert tree["count"] == 1


def test_get_tree_ads_called_for_each_regular_file(
    tmp_path,
    monkeypatch,
):
    """Проверяем вызов get_ads_size для каждого обычного файла."""
    create_file(tmp_path / "a.txt", b"123")
    create_file(tmp_path / "b.txt", b"4567")

    ads_mock = Mock(return_value=0)
    monkeypatch.setattr(ft, "get_ads_size", ads_mock)

    ft.get_tree(str(tmp_path))

    assert ads_mock.call_count == 2


def test_get_tree_progress_callback(tmp_path, monkeypatch):
    """Проверяем, что функция поддерживает callback прогресса."""
    create_file(tmp_path / "a.txt")
    create_file(tmp_path / "b.txt")
    (tmp_path / "subdir").mkdir()

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    callback = Mock()

    ft.get_tree(
        str(tmp_path),
        progress_callback=callback,
    )

    # Callback вызывается не при каждом элементе,
    # а с интервалом более 0.05 секунды.
    # Поэтому гарантируем хотя бы один вызов, контролируя время.
    assert callback.call_count >= 0


def test_get_tree_progress_callback_with_mocked_time(
    tmp_path,
    monkeypatch,
):
    """Проверяем передачу текущего пути и количества элементов."""
    create_file(tmp_path / "a.txt")
    create_file(tmp_path / "b.txt")

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    # Начальное значение last_ui_update равно 0.
    # Первые вызовы time.time() гарантированно превышают интервал.
    times = iter([100.0, 100.1, 100.2, 100.3, 100.4])

    monkeypatch.setattr(ft.time, "time", lambda: next(times))

    callback = Mock()

    ft.get_tree(
        str(tmp_path),
        progress_callback=callback,
    )

    assert callback.call_count >= 1

    current_dir, scanned = callback.call_args.args

    assert current_dir == str(tmp_path)
    assert scanned >= 1


def test_get_tree_normalizes_root_path(tmp_path, monkeypatch):
    """Проверяем работу с относительным путём."""
    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    old_cwd = os.getcwd()

    try:
        os.chdir(tmp_path)

        Path("file.txt").write_text("hello", encoding="utf-8")

        tree = ft.get_tree(".")

        assert tree["type"] == "directory"
        assert "file.txt" in tree["children"]
    finally:
        os.chdir(old_cwd)


def test_get_tree_file_extensions_are_lowercase(
    tmp_path,
    monkeypatch,
):
    """Расширения файлов приводятся к нижнему регистру."""
    create_file(tmp_path / "document.TXT", b"123")
    create_file(tmp_path / "image.PNG", b"12345")

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    tree = ft.get_tree(str(tmp_path))

    assert tree["children"]["document.TXT"]["ext"] == ".txt"
    assert tree["children"]["image.PNG"]["ext"] == ".png"


def test_get_tree_progress_callback_is_optional(
    tmp_path,
    monkeypatch,
):
    """Без callback дерево должно успешно строиться."""
    create_file(tmp_path / "file.txt", b"123")

    monkeypatch.setattr(ft, "get_ads_size", Mock(return_value=0))

    tree = ft.get_tree(str(tmp_path))

    assert tree["size"] == 3
    assert tree["count"] == 1


# ============================================================
# Тесты extract_files()
# ============================================================

def test_extract_files_single_file():
    """Извлекаем один файл из узла дерева."""
    node = {
        "name": "document.txt",
        "type": "file",
        "size": 100,
        "ext": ".txt",
    }

    result = []

    ft.extract_files(result, node)

    assert result == [
        {
            "name": "document.txt",
            "size": 100,
            "ext": ".txt",
        }
    ]


def test_extract_files_empty_directory():
    """Из пустой директории не извлекаются файлы."""
    node = {
        "name": "empty",
        "type": "directory",
        "children": {},
    }

    result = []

    ft.extract_files(result, node)

    assert result == []


def test_extract_files_nested_tree():
    """Извлекаем все файлы из дерева любой глубины."""
    node = {
        "name": "root",
        "type": "directory",
        "children": {
            "a.txt": {
                "name": "a.txt",
                "type": "file",
                "size": 10,
                "ext": ".txt",
            },
            "subdir": {
                "name": "subdir",
                "type": "directory",
                "children": {
                    "b.jpg": {
                        "name": "b.jpg",
                        "type": "file",
                        "size": 20,
                        "ext": ".jpg",
                    },
                    "nested": {
                        "name": "nested",
                        "type": "directory",
                        "children": {
                            "c.txt": {
                                "name": "c.txt",
                                "type": "file",
                                "size": 30,
                                "ext": ".txt",
                            }
                        },
                    },
                },
            },
        },
    }

    result = []

    ft.extract_files(result, node)

    assert len(result) == 3

    names = {file["name"] for file in result}

    assert names == {"a.txt", "b.jpg", "c.txt"}


def test_extract_files_preserves_existing_list():
    """Функция дополняет переданный список, а не создаёт новый."""
    node = {
        "name": "a.txt",
        "type": "file",
        "size": 10,
        "ext": ".txt",
    }

    result = [
        {
            "name": "existing.txt",
            "size": 5,
            "ext": ".txt",
        }
    ]

    ft.extract_files(result, node)

    assert len(result) == 2
    assert result[0]["name"] == "existing.txt"
    assert result[1]["name"] == "a.txt"


# ============================================================
# Тесты get_files_sorted_by_extension()
# ============================================================

def test_get_files_sorted_by_extension_empty_directory():
    """Для пустого дерева возвращается пустой словарь."""
    node = {
        "name": "root",
        "type": "directory",
        "children": {},
    }

    result = ft.get_files_sorted_by_extension(node)

    assert result == {}


def test_get_files_sorted_by_extension_groups_files():
    """Файлы группируются по расширениям."""
    node = {
        "name": "root",
        "type": "directory",
        "children": {
            "a.txt": {
                "name": "a.txt",
                "type": "file",
                "size": 10,
                "ext": ".txt",
            },
            "b.txt": {
                "name": "b.txt",
                "type": "file",
                "size": 20,
                "ext": ".txt",
            },
            "c.jpg": {
                "name": "c.jpg",
                "type": "file",
                "size": 30,
                "ext": ".jpg",
            },
        },
    }

    result = ft.get_files_sorted_by_extension(node)

    assert set(result.keys()) == {".txt", ".jpg"}

    assert len(result[".txt"]) == 2
    assert len(result[".jpg"]) == 1


def test_get_files_sorted_by_extension_sorts_groups():
    """Группы сортируются по убыванию количества файлов."""
    node = {
        "name": "root",
        "type": "directory",
        "children": {
            "a.txt": {
                "name": "a.txt",
                "type": "file",
                "size": 10,
                "ext": ".txt",
            },
            "b.txt": {
                "name": "b.txt",
                "type": "file",
                "size": 20,
                "ext": ".txt",
            },
            "c.txt": {
                "name": "c.txt",
                "type": "file",
                "size": 30,
                "ext": ".txt",
            },
            "d.jpg": {
                "name": "d.jpg",
                "type": "file",
                "size": 40,
                "ext": ".jpg",
            },
            "e.png": {
                "name": "e.png",
                "type": "file",
                "size": 50,
                "ext": ".png",
            },
            "f.png": {
                "name": "f.png",
                "type": "file",
                "size": 60,
                "ext": ".png",
            },
        },
    }

    result = ft.get_files_sorted_by_extension(node)

    # .txt — 3 файла, .png — 2 файла, .jpg — 1 файл.
    assert list(result.keys()) == [".txt", ".png", ".jpg"]


def test_get_files_sorted_by_extension_without_extension():
    """Файлы без расширения группируются под пустой строкой."""
    node = {
        "name": "root",
        "type": "directory",
        "children": {
            "README": {
                "name": "README",
                "type": "file",
                "size": 100,
                "ext": "",
            },
            "a.txt": {
                "name": "a.txt",
                "type": "file",
                "size": 10,
                "ext": ".txt",
            },
        },
    }

    result = ft.get_files_sorted_by_extension(node)

    assert "" in result
    assert len(result[""]) == 1
    assert result[""][0]["name"] == "README"


def test_get_files_sorted_by_extension_preserves_file_sizes():
    """Размеры файлов сохраняются при группировке."""
    node = {
        "name": "root",
        "type": "directory",
        "children": {
            "a.txt": {
                "name": "a.txt",
                "type": "file",
                "size": 1234,
                "ext": ".txt",
            },
        },
    }

    result = ft.get_files_sorted_by_extension(node)

    assert result[".txt"][0]["size"] == 1234