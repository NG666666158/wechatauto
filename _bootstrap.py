from __future__ import annotations

import os
from pathlib import Path


def configure_comtypes_cache(project_root: str | Path) -> str:
    """Redirect comtypes generated cache into the repository.

    Some locked-down Windows environments deny writes to the default
    `%APPDATA%\\Python\\PythonXY\\comtypes_cache` location. We patch the
    internal resolver before `comtypes.client` is imported so pywinauto can
    initialize normally.
    """

    root = Path(project_root).resolve()
    cache_dir = root / ".cache" / "comtypes"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        from comtypes.client import _code_cache
    except Exception:
        return str(cache_dir)

    original_create = _code_cache._create_comtypes_gen_package

    def _repo_gen_dir() -> str:
        original_create()
        from comtypes import gen

        gen_path = list(gen.__path__)
        if str(cache_dir) not in gen_path:
            gen_path.append(str(cache_dir))
            gen.__path__ = gen_path
        return str(cache_dir)

    _code_cache._find_gen_dir = _repo_gen_dir
    os.environ.setdefault("PYWECHAT_COMTYPES_CACHE", str(cache_dir))
    return str(cache_dir)
