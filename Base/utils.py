def format_size(size: float) -> str:
    """Человекочитаемый размер: 1536 -> '1.50 KB'."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"
