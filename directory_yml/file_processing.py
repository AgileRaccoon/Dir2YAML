import os
import fnmatch
import time
import hashlib

EXCLUDED_DIRS = [
    ".git",
    ".venv",
    "node_modules",
    ".idea",
    ".vscode",
    ".DS_Store",
    ".github",
    "__pycache__"
]

def collect_directory_structures(
    directories,
    ignore_patterns,
    progress_callback=None,
    max_file_size_bytes=None
):
    """
    複数ディレクトリを走査し、それぞれを「ルートディレクトリ」として構造を取得。
    """
    results = []
    for root_dir in directories:
        if os.path.isdir(root_dir):
            if progress_callback:
                progress_callback(f"ディレクトリ走査開始: {root_dir}")
            root_name = os.path.basename(os.path.normpath(root_dir))
            structure = {
                "root": root_name,
                "children": _walk_directory(
                    root_dir,
                    current_dir=root_dir,
                    ignore_patterns=ignore_patterns,
                    progress_callback=progress_callback,
                    max_file_size_bytes=max_file_size_bytes
                )
            }
            results.append(structure)
    return results


def _walk_directory(
    root_dir,
    current_dir,
    ignore_patterns,
    progress_callback,
    max_file_size_bytes
):
    rel_path = os.path.relpath(current_dir, root_dir)  # root_dirからの相対パス
    if rel_path == ".":
        rel_path = ""

    dir_name = os.path.basename(os.path.normpath(current_dir))
    structure = {
        "type": "directory",
        "name": dir_name if rel_path else ".",
        "rel_path": rel_path,
        "children": []
    }

    try:
        items = os.listdir(current_dir)
    except PermissionError:
        if progress_callback:
            progress_callback(f"[アクセス拒否] {current_dir}")
        return structure

    for item in sorted(items):
        full_path = os.path.join(current_dir, item)
        time.sleep(0)

        # EXCLUDED_DIRS にマッチするフォルダは中身を無視
        if item in EXCLUDED_DIRS and os.path.isdir(full_path):
            if progress_callback:
                progress_callback(f"スキップ(フォルダのみ存在表示): {full_path}")
            skipped_rel_path = os.path.relpath(full_path, root_dir)
            structure["children"].append({
                "type": "directory",
                "name": item,
                "rel_path": skipped_rel_path,
                "children": []
            })
            continue

        if _is_ignored(item, ignore_patterns):
            if progress_callback:
                progress_callback(f"スキップ(パターン一致): {full_path}")
            continue

        if os.path.isdir(full_path):
            if progress_callback:
                progress_callback(f"ディレクトリ: {full_path}")
            structure["children"].append(
                _walk_directory(
                    root_dir,
                    full_path,
                    ignore_patterns,
                    progress_callback,
                    max_file_size_bytes
                )
            )
        else:
            structure["children"].append(
                _process_file(
                    root_dir,
                    full_path,
                    max_file_size_bytes,
                    progress_callback
                )
            )

    return structure


def _process_file(
    root_dir,
    file_path,
    max_file_size_bytes,
    progress_callback
):
    file_name = os.path.basename(file_path)
    rel_path = os.path.relpath(file_path, root_dir)

    if progress_callback:
        progress_callback(f"ファイル: {file_path}")

    stat_info = os.stat(file_path)
    file_size = stat_info.st_size
    mtime = stat_info.st_mtime
    file_hash = _calc_sha256(file_path)

    file_data = {
        "type": "file",
        "name": file_name,
        "rel_path": rel_path,
        "size": file_size,
        "mtime": mtime,
        "sha256": file_hash,
        "content": None
    }

    # スキップ対象例
    skip_by_name = [".env", ".htpasswd"]
    if file_name.endswith(".log"):
        skip_by_name.append(file_name)

    if file_name in skip_by_name:
        file_data["content"] = "[SKIPPED by name]"
        return file_data

    if max_file_size_bytes is not None and file_size > max_file_size_bytes:
        file_data["content"] = "[SKIPPED due to size]"
        return file_data

    try:
        with open(file_path, "rb") as fb:
            raw_data = fb.read()
            if b"\0" in raw_data:
                file_data["content"] = "[SKIPPED or BINARY]"
            else:
                text_data = raw_data.decode("utf-8", errors="replace")
                file_data["content"] = text_data
    except Exception:
        file_data["content"] = "[SKIPPED or BINARY]"

    return file_data


def _calc_sha256(file_path):
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception:
        return None


def _is_ignored(item_name, ignore_patterns):
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(item_name, pattern):
            return True
    return False
