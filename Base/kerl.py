import os
import time
from pathlib import Path
import concurrent.futures          # Это у вас уже, скорее всего, есть
import concurrent                  # <--- ДОБАВЬТЕ ЭТУ СТРОКУ
from concurrent.futures import ThreadPoolExecutor
import threading
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

    nodes = {root_path: tree}
    tree_lock = threading.Lock()

    ui_lock = threading.Lock()
    last_ui_update = [0.0]
    total_scanned = [0]

    def scan_directory(current_dir):
        """Функция для обработки ОДНОЙ директории. Будет выполняться в пуле потоков."""
        try:
            # os.scandir эффективнее, чем os.listdir, так как сразу возвращает объекты с метаданными
            with os.scandir(current_dir) as entries:
                entries_list = list(entries)
        except OSError:
            return []  # Нет доступа к папке

        local_files = []
        local_dirs = []

        # Сначала быстро разделяем объекты
        for entry in entries_list:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_file():
                    local_files.append(entry)
                elif entry.is_dir():
                    local_dirs.append(entry)
            except OSError:
                continue

        local_scanned_count = len(local_files) + len(local_dirs)
        if progress_callback:
            with ui_lock:
                total_scanned[0] += local_scanned_count
                current_time = time.time()
                if current_time - last_ui_update[0] > 0.05:
                    progress_callback(current_dir, total_scanned[0])
                    last_ui_update[0] = current_time

        # Получаем текущий узел из общего дерева
        with tree_lock:
            current_node = nodes.get(current_dir)
        if not current_node:
            return []

        current_depth = current_node["depth"]
        dir_files_size = 0
        dir_files_count = 0

        # 1. Обрабатываем файлы в текущей директории
        for entry in local_files:
            try:
                stat = entry.stat()
                f_size = stat.st_size
                ext = os.path.splitext(entry.name)[1].lower()

                # Наша интеграция ADS (выполняется параллельно!)
                ads_size = get_ads_size(entry.path)
                full_size = f_size + ads_size

                with tree_lock:
                    current_node["children"][entry.name] = {
                        "name": entry.name,
                        "type": "file",
                        "size": full_size,
                        "ads_size": ads_size,
                        "depth": current_depth + 1,
                        "mtime": stat.st_mtime,
                        "owner": "User" if is_nt else Path(entry.path).owner(),
                        "ext": ext
                    }
                dir_files_size += full_size
                dir_files_count += 1
            except OSError:
                continue

        # 2. Создаем «заглушки» для поддиректорий и собираем пути для дальнейшего сканирования
        next_dirs_to_scan = []
        for entry in local_dirs:
            try:
                stat = entry.stat()
                new_dir_node = {
                    "name": entry.name,
                    "type": "directory",
                    "size": 0,
                    "count": 0,
                    "depth": current_depth + 1,
                    "mtime": stat.st_mtime,
                    "owner": "User" if is_nt else Path(entry.path).owner(),
                    "children": {}
                }
                with tree_lock:
                    current_node["children"][entry.name] = new_dir_node
                    nodes[entry.path] = new_dir_node

                next_dirs_to_scan.append(entry.path)
            except OSError:
                continue

        if dir_files_size > 0:
            with tree_lock:
                temp_path = current_dir
                while temp_path in nodes:
                    nodes[temp_path]["size"] += dir_files_size
                    nodes[temp_path]["count"] += dir_files_count
                    if temp_path == root_path:
                        break
                    temp_path = os.path.dirname(temp_path)

        return next_dirs_to_scan

    max_workers = (os.cpu_count() or 4) * 4

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Очередь задач на обработку директорий. Стартуем с корня.
        futures = {executor.submit(scan_directory, root_path)}

        while futures:
            done, _ = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)

            for future in done:
                futures.remove(future)
                try:
                    next_dirs = future.result()
                    for d_path in next_dirs:
                        futures.add(executor.submit(scan_directory, d_path))
                except Exception as e:
                    print(f"Ошибка при сканировании: {e}")

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