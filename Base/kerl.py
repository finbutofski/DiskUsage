import os
import time
from pathlib import Path
from ads_support import *


def count_items(root_path):
    """Быстрый подсчет общего количества файлов и папок для прогресс-бара"""
    total = 0
    for _, dirs, files in os.walk(root_path):
        total += len(dirs) + len(files)
    return total


def get_tree(root_path, progress_callback=None):
    root_path = os.path.abspath(root_path)
    is_nt = os.name == 'nt'

    # Корень дерева
    tree = {
        "name": os.path.basename(root_path) or root_path,
        "type": "directory",
        "size": 0,
        "count": 0,
        "depth": 0,
        "mtime": os.path.getmtime(root_path),
        "owner": "User" if is_nt else Path(root_path).owner(),
        "children": {}
    }

    # Реестр нод для быстрого доступа по путям
    nodes = {root_path: tree}
    last_ui_update = 0
    total_scanned = 0

    # Классический os.walk гарантирует последовательный обход сверху вниз
    for current_dir, dirs, files in os.walk(root_path):
        if current_dir not in nodes:
            continue

        current_node = nodes[current_dir]
        current_depth = current_node["depth"]

        dir_files_size = 0
        dir_files_count = 0

        # 1. Обрабатываем файлы в текущей папке
        for f in files:
            file_path = os.path.join(current_dir, f)
            total_scanned += 1

            # Плавное обновление UI (каждые 50 мс)
            if progress_callback:
                current_time = time.time()
                if current_time - last_ui_update > 0.05:
                    progress_callback(current_dir, total_scanned)
                    last_ui_update = current_time

            try:
                if os.path.islink(file_path):
                    continue

                stat = os.stat(file_path)
                f_size = stat.st_size
                ext = os.path.splitext(f)[1].lower()

                # --- ЧЕСТНЫЙ ПОДСЧЕТ ADS ---
                ads_size = get_ads_size(file_path)
                full_size = f_size + ads_size
                # ---------------------------

                current_node["children"][f] = {
                    "name": f,
                    "type": "file",
                    "size": full_size,
                    "ads_size": ads_size,
                    "depth": current_depth + 1,
                    "mtime": stat.st_mtime,
                    "owner": "User" if is_nt else Path(file_path).owner(),
                    "ext": ext
                }

                dir_files_size += full_size
                dir_files_count += 1

            except OSError:
                continue

        # 2. Обрабатываем папки в текущей директории (создаем заглушки)
        for d in dirs:
            dir_path = os.path.join(current_dir, d)
            total_scanned += 1

            try:
                stat = os.stat(dir_path)
                new_dir_node = {
                    "name": d,
                    "type": "directory",
                    "size": 0,
                    "count": 0,
                    "depth": current_depth + 1,
                    "mtime": stat.st_mtime,
                    "owner": "User" if is_nt else Path(dir_path).owner(),
                    "children": {}
                }
                current_node["children"][d] = new_dir_node
                nodes[dir_path] = new_dir_node
            except OSError:
                continue

    # --- ФИНАЛЬНЫЙ СБОР РАЗМЕРОВ (Снизу Вверх) ---
    # Постобработка дерева гарантирует, что размеры всех подпапок сложатся абсолютно точно
    def calculate_sizes_post_order(node):
        if node["type"] == "file":
            return node["size"], 1

        total_size = 0
        total_count = 0

        for child in node["children"].values():
            child_size, child_count = calculate_sizes_post_order(child)
            total_size += child_size
            total_count += child_count

        node["size"] = total_size
        node["count"] = total_count
        return total_size, total_count

    calculate_sizes_post_order(tree)
    return tree


def extract_files(all_files, current_node):
    if current_node['type'] == 'file':
        all_files.append({
            'name': current_node['name'],
            'size': current_node['size'],
            'ext': current_node.get('ext', '')
        })
    elif current_node['type'] == 'directory':
        for child in current_node['children'].values():
            extract_files(all_files, child)


def get_files_sorted_by_extension(node):
    all_files = []
    result = {}
    extract_files(all_files, node)
    for el in all_files:
        if el['ext'] not in result:
            result[el['ext']] = []
        result[el['ext']].append(el)
    return dict(sorted(result.items(), key=lambda item: -len(item[1])))