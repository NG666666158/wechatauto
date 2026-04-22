from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
USERS_DIR = DATA_DIR / "users"
AGENTS_DIR = DATA_DIR / "agents"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
MEMORY_DIR = DATA_DIR / "memory"
LOGS_DIR = DATA_DIR / "logs"

def local_data_dirs() -> tuple[Path, ...]:
    return (
        DATA_DIR,
        USERS_DIR,
        AGENTS_DIR,
        KNOWLEDGE_DIR,
        MEMORY_DIR,
        LOGS_DIR,
    )


def bootstrap_data_dirs() -> tuple[Path, ...]:
    directories = local_data_dirs()
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return directories
