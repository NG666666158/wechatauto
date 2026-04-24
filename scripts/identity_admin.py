from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from wechat_ai.identity.identity_admin import main  # type: ignore  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
