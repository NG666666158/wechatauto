from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _normalize(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    return value


def main() -> int:
    from wechat_ai.app.service import DesktopAppService

    service = DesktopAppService()
    now = datetime.now()
    payload = {
        "app_status": _normalize(service.get_app_status()),
        "daemon_status": _normalize(service.get_daemon_status()),
        "schedule_status": _normalize(service.get_schedule_status(now=now)),
        "tray_state": _normalize(service.get_tray_state(now=now)),
        "settings": _normalize(service.get_settings()),
        "knowledge_status": _normalize(service.get_knowledge_status()),
        "customers": [_normalize(item) for item in service.list_customers()],
        "identity_drafts": service.list_identity_drafts(),
        "identity_candidates": service.list_identity_candidates(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
