import os
import time
from pathlib import Path


def get_tree(root_path):
    root_path = os.path.abspath(root_path)
    base_depth = root_path.count(os.sep)

    tree = {
        "name": os.path.basename(root_path) or root_path,
        "type": "directory",
        "size": 0,
        "count": 0,
        "depth": 0,
        "mtime": os.path.getmtime(root_path),
        "owner": Path(root_path).owner() if os.name != 'nt' else "User",
        "children": {}
    }

    nodes = {root_path: tree}

    for current_dir, dirs, files in os.walk(root_path):
        if current_dir not in nodes:
            continue

        current_node = nodes[current_dir]
        # Вычисляем текущую глубину относительно корня
        current_depth = current_dir.count(os.sep) - base_depth

        for f in files:
            file_path = os.path.join(current_dir, f)
            try:
                if os.path.islink(file_path): continue

                stat = os.stat(file_path)
                f_size = stat.st_size

                current_node["children"][f] = {
                    "name": f,
                    "type": "file",
                    "size": f_size,
                    "depth": current_depth + 1,
                    "mtime": stat.st_mtime,
                    "owner": Path(file_path).owner() if os.name != 'nt' else "User",
                    "ext": Path(f).suffix.lower()
                }

                temp_path = current_dir
                while temp_path in nodes:
                    nodes[temp_path]["size"] += f_size
                    nodes[temp_path]["count"] += 1
                    if temp_path == root_path: break
                    temp_path = os.path.dirname(temp_path)

            except OSError:
                continue

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
                    "owner": Path(dir_path).owner() if os.name != 'nt' else "User",
                    "children": {}
                }
                current_node["children"][d] = new_dir_node
                nodes[dir_path] = new_dir_node
            except OSError:
                continue

    return tree

def _calculate_ratios(node, total_size):
    """Рекурсивная функция для расчета процентов"""
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
