from Base.kerl import get_tree
from Base.kerl import get_files_sorted_by_extension

tree = get_tree("D:\\")
files_by_extension = get_files_sorted_by_extension(tree)

for repos in tree['children'].values():
    if repos['type'] == 'directory':
        print(f"name: {repos['name']:<25} | size: {repos['size']:<20} | filecount: {len(repos['children']):<10}")
    else:
        print(f"name: {repos['name']:<25} | size: {repos['size']:<20}")
# print(f"{'ИМЯ ФАЙЛА':<50} | {'РАЗМЕР'}")
# print("-" * 65)
print("\n\n")

for key, value in files_by_extension.items(): # Берем только первые 15 элементов
    # Для удобства переведем в Мегабайты
    print(f"{key:<10} | filescount:{len(value)}")