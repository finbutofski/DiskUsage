import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


def scan_single_folder_sync(root_path, progress_callback=None):
    """Быстрый синхронный обход отдельной подпапки через os.walk"""
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
    last_ui_update = time.time()

    for current_dir, dirs, files in os.walk(root_path):
        if current_dir not in nodes:
            continue

        current_node = nodes[current_dir]
        current_depth = current_node["depth"]

        if progress_callback:
            current_time = time.time()
            if current_time - last_ui_update > 0.2:  # Защита от спама в UI
                progress_callback(os.path.basename(current_dir))
                last_ui_update = current_time

        dir_files_size = 0
        dir_files_count = 0

        # Сбор файлов
        for f in files:
            file_path = os.path.join(current_dir, f)
            try:
                if os.path.islink(file_path):
                    continue

                stat = os.stat(file_path)
                f_size = stat.st_size
                ext = os.path.splitext(f)[1].lower()

                current_node["children"][f] = {
                    "name": f,
                    "type": "file",
                    "size": f_size,
                    "depth": current_depth + 1,
                    "mtime": stat.st_mtime,
                    "owner": "User" if is_nt else Path(file_path).owner(),
                    "ext": ext
                }

                dir_files_size += f_size
                dir_files_count += 1
            except OSError:
                continue

        # Каскадный подъем размеров вверх по дереву этой ветки
        if dir_files_size > 0:
            temp_path = current_dir
            while temp_path in nodes:
                nodes[temp_path]["size"] += dir_files_size
                nodes[temp_path]["count"] += dir_files_count
                if temp_path == root_path:
                    break
                temp_path = os.path.dirname(temp_path)

        # Подготовка структуры для подпапок
        for d in dirs:
            dir_path = os.path.join(current_dir, d)
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

    return tree


def get_tree_parallel(root_path, progress_callback=None, max_workers=16):
    """Главная многопоточная точка входа"""
    root_path = os.path.abspath(root_path)
    is_nt = os.name == 'nt'

    root_tree = {
        "name": os.path.basename(root_path) or root_path,
        "type": "directory",
        "size": 0,
        "count": 0,
        "depth": 0,
        "mtime": os.path.getmtime(root_path),
        "owner": "User" if is_nt else Path(root_path).owner(),
        "children": {}
    }

    try:
        entries = list(os.scandir(root_path))
    except OSError:
        return root_tree

    subfolders = []
    root_files_size = 0
    root_files_count = 0

    # 1. Сначала обрабатываем файлы в самом корне
    for entry in entries:
        try:
            # ИСПРАВЛЕНО: у DirEntry метод называется is_symlink(), а не is_link()
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                subfolders.append(entry.path)
            else:
                stat = entry.stat()
                f_size = stat.st_size
                root_files_size += f_size
                root_files_count += 1
                root_tree["children"][entry.name] = {
                    "name": entry.name,
                    "type": "file",
                    "size": f_size,
                    "depth": 1,
                    "mtime": stat.st_mtime,
                    "owner": "User" if is_nt else Path(entry.path).owner(),
                    "ext": os.path.splitext(entry.name)[1].lower()
                }
        except OSError:
            continue

    root_tree["size"] += root_files_size
    root_tree["count"] += root_files_count

    # 2. А теперь параллельно запускаем сканирование крупных подпапок
    if subfolders:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scan_single_folder_sync, folder, progress_callback): folder
                for folder in subfolders
            }

            for future in futures:
                folder_path = futures[future]
                dirname = os.path.basename(folder_path)
                try:
                    sub_tree = future.result()
                    # ИСПРАВЛЕНО: корректное присвоение в дерево
                    root_tree["children"][dirname] = sub_tree
                    root_tree["size"] += sub_tree.get("size", 0)
                    root_tree["count"] += sub_tree.get("count", 0)
                except Exception as e:
                    # Если папка заблокирована, покажем ошибку прямо в интерфейсе вместо падения
                    root_tree["children"][dirname] = {
                        "name": dirname,
                        "type": "directory",
                        "size": 0,
                        "children": {},
                        "owner": f"Error: {str(e)}"
                    }

    return root_tree


def _calculate_ratios(node, total_size):
    if total_size == 0:
        node["ratio"] = 0
    else:
        node["ratio"] = (node["size"] / total_size) * 100
    if node["type"] == "directory":
        for child in node["children"].values():
            _calculate_ratios(child, total_size)


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


def get_files_sorted_by_size(node):
    if 'children' in node and node['children']:
        node['children'] = dict(sorted(
            node['children'].items(),
            key=lambda item: item[1]['size'],
            reverse=True
        ))
    return node