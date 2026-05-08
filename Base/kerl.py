import os
from pathlib import Path


def get_tree(root_path):
    root_path = os.path.abspath(root_path)
    tree = {
        "name": os.path.basename(root_path) or root_path,
        "type": "directory",
        "size": 0,
        "children": {}
    }

    nodes = {root_path: tree}

    for current_dir, dirs, files in os.walk(root_path):
        if current_dir not in nodes:
            continue

        current_node = nodes[current_dir]

        for f in files:
            file_path = os.path.join(current_dir, f)
            try:
                if os.path.islink(file_path): continue

                f_size = os.path.getsize(file_path)

                current_node["children"][f] = {
                    "name": f,
                    "type": "file",
                    "size": f_size,
                    "ext": Path(f).suffix.lower()
                }

                temp_path = current_dir
                while temp_path in nodes:
                    nodes[temp_path]["size"] += f_size
                    if temp_path == root_path: break
                    temp_path = os.path.dirname(temp_path)

            except OSError:
                continue

        for d in dirs:
            dir_path = os.path.join(current_dir, d)
            new_dir_node = {
                "name": d,
                "type": "directory",
                "size": 0,
                "children": {}
            }
            current_node["children"][d] = new_dir_node
            nodes[dir_path] = new_dir_node

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
    return result
