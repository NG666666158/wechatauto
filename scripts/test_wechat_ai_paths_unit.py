from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_path_constants() -> None:
    from wechat_ai import paths

    expected_root = Path(paths.__file__).resolve().parent
    assert paths.ROOT == expected_root
    assert paths.DATA_DIR == expected_root / "data"
    assert paths.USERS_DIR == paths.DATA_DIR / "users"
    assert paths.AGENTS_DIR == paths.DATA_DIR / "agents"
    assert paths.SELF_IDENTITY_DIR == paths.DATA_DIR / "self_identity"
    assert paths.KNOWLEDGE_DIR == paths.DATA_DIR / "knowledge"
    assert paths.KNOWLEDGE_UPLOADS_DIR == paths.KNOWLEDGE_DIR / "uploads"
    assert paths.APP_DIR == paths.DATA_DIR / "app"
    assert paths.MEMORY_DIR == paths.DATA_DIR / "memory"
    assert paths.LOGS_DIR == paths.DATA_DIR / "logs"


def test_bootstrap_data_dirs_creates_missing_directories() -> None:
    from wechat_ai import paths

    scratch_root = ROOT / ".tmp_wechat_ai_paths_bootstrap"
    if scratch_root.exists():
        shutil.rmtree(scratch_root, ignore_errors=True)

    root = scratch_root / "wechat_ai"
    data_dir = root / "data"
    users_dir = data_dir / "users"
    agents_dir = data_dir / "agents"
    self_identity_dir = data_dir / "self_identity"
    knowledge_dir = data_dir / "knowledge"
    knowledge_uploads_dir = knowledge_dir / "uploads"
    app_dir = data_dir / "app"
    memory_dir = data_dir / "memory"
    logs_dir = data_dir / "logs"

    original_values = {
        "ROOT": paths.ROOT,
        "DATA_DIR": paths.DATA_DIR,
        "USERS_DIR": paths.USERS_DIR,
        "AGENTS_DIR": paths.AGENTS_DIR,
        "SELF_IDENTITY_DIR": paths.SELF_IDENTITY_DIR,
        "KNOWLEDGE_DIR": paths.KNOWLEDGE_DIR,
        "KNOWLEDGE_UPLOADS_DIR": paths.KNOWLEDGE_UPLOADS_DIR,
        "APP_DIR": paths.APP_DIR,
        "MEMORY_DIR": paths.MEMORY_DIR,
        "LOGS_DIR": paths.LOGS_DIR,
    }

    try:
        paths.ROOT = root
        paths.DATA_DIR = data_dir
        paths.USERS_DIR = users_dir
        paths.AGENTS_DIR = agents_dir
        paths.SELF_IDENTITY_DIR = self_identity_dir
        paths.KNOWLEDGE_DIR = knowledge_dir
        paths.KNOWLEDGE_UPLOADS_DIR = knowledge_uploads_dir
        paths.APP_DIR = app_dir
        paths.MEMORY_DIR = memory_dir
        paths.LOGS_DIR = logs_dir

        created = paths.bootstrap_data_dirs()

        assert created == (
            data_dir,
            users_dir,
            agents_dir,
            self_identity_dir,
            knowledge_dir,
            knowledge_uploads_dir,
            app_dir,
            memory_dir,
            logs_dir,
        )
        for directory in created:
            assert directory.exists()
            assert directory.is_dir()
    finally:
        for name, value in original_values.items():
            setattr(paths, name, value)
        if scratch_root.exists():
            shutil.rmtree(scratch_root, ignore_errors=True)


def main() -> None:
    test_path_constants()
    test_bootstrap_data_dirs_creates_missing_directories()
    print("wechat_ai paths unit tests passed")


if __name__ == "__main__":
    main()
