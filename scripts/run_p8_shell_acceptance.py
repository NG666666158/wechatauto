from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SETTINGS_PAGE = ROOT / "desktop_app" / "frontend" / "app" / "settings" / "page.tsx"
SHELL_BRIDGE = ROOT / "desktop_app" / "frontend" / "lib" / "electron-shell.ts"
WINDOW_DIAGNOSTICS = ROOT / "desktop_app" / "electron" / "window-diagnostics.cjs"
REQUIRED_LABELS = ("开机自启", "定时巡检间隔")
REQUIRED_SETTINGS_TOKENS = ("launchAtLogin", "scheduleTickIntervalSeconds")
REQUIRED_DIAGNOSTIC_EVENTS = (
    "window.did_start_loading",
    "window.dom_ready",
    "window.did_finish_load",
    "window.did_fail_load",
)


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def inspect_settings_source() -> dict[str, Any]:
    source = SETTINGS_PAGE.read_text(encoding="utf-8")
    bridge_source = SHELL_BRIDGE.read_text(encoding="utf-8")
    missing_labels = [label for label in REQUIRED_LABELS if label not in source]
    missing_tokens = [token for token in REQUIRED_SETTINGS_TOKENS if token not in source]
    missing_bridge_tokens = [
        token
        for token in ("getPreferences", "updatePreferences")
        if token not in bridge_source
    ]
    return {
        "settings_page": str(SETTINGS_PAGE),
        "shell_bridge": str(SHELL_BRIDGE),
        "labels_present": not missing_labels,
        "settings_tokens_present": not missing_tokens,
        "bridge_tokens_present": not missing_bridge_tokens,
        "missing_labels": missing_labels,
        "missing_settings_tokens": missing_tokens,
        "missing_bridge_tokens": missing_bridge_tokens,
    }


def inspect_window_diagnostics() -> dict[str, Any]:
    source = WINDOW_DIAGNOSTICS.read_text(encoding="utf-8")
    missing_events = [event_name for event_name in REQUIRED_DIAGNOSTIC_EVENTS if event_name not in source]
    return {
        "file": str(WINDOW_DIAGNOSTICS),
        "events_present": not missing_events,
        "missing_events": missing_events,
    }


def probe_frontend_settings(frontend_url: str, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    try:
        with urlopen(frontend_url, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            status_code = getattr(response, "status", 200)
            headers = dict(response.headers.items())
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status_code = exc.code
        headers = dict(exc.headers.items())
        reachable = False
        error = f"HTTPError: {exc.code}"
    except URLError as exc:
        return {
            "requested_url": frontend_url,
            "reachable": False,
            "status_code": None,
            "content_type": "",
            "labels_present": False,
            "label_hits": {label: False for label in REQUIRED_LABELS},
            "error": f"URLError: {exc.reason}",
        }
    else:
        reachable = True
        error = ""

    label_hits = {label: label in body for label in REQUIRED_LABELS}
    return {
        "requested_url": frontend_url,
        "reachable": reachable,
        "status_code": status_code,
        "content_type": headers.get("Content-Type", ""),
        "labels_present": all(label_hits.values()),
        "label_hits": label_hits,
        "error": error,
    }


def build_shell_acceptance_report(
    *,
    frontend_url: str = "http://127.0.0.1:3000/settings",
    skip_http: bool = False,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    settings_source = inspect_settings_source()
    diagnostics = inspect_window_diagnostics()
    frontend_probe = (
        {
            "requested_url": frontend_url,
            "reachable": None,
            "status_code": None,
            "content_type": "",
            "labels_present": None,
            "label_hits": {},
            "error": "skipped",
        }
        if skip_http
        else probe_frontend_settings(frontend_url, timeout_seconds=timeout_seconds)
    )

    failures: list[str] = []
    if not settings_source["labels_present"]:
        failures.append("settings_labels_missing")
    if not settings_source["settings_tokens_present"]:
        failures.append("settings_tokens_missing")
    if not settings_source["bridge_tokens_present"]:
        failures.append("shell_bridge_tokens_missing")
    if not diagnostics["events_present"]:
        failures.append("window_diagnostics_events_missing")
    if not skip_http:
        if not frontend_probe["reachable"]:
            failures.append("frontend_settings_unreachable")
        elif not frontend_probe["labels_present"]:
            failures.append("frontend_settings_labels_missing")

    return {
        "script": "p8_shell_acceptance",
        "safe_read_only": True,
        "does_not_send_messages": True,
        "accepted": not failures,
        "frontend_url": frontend_url,
        "checks": {
            "settings_source": settings_source,
            "window_diagnostics": diagnostics,
            "frontend_probe": frontend_probe,
        },
        "failures": failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run P8 desktop shell acceptance checks.")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000/settings")
    parser.add_argument("--skip-http", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--format", choices=("json", "pretty"), default="json")
    return parser


def main() -> int:
    _configure_utf8_stdio()
    args = build_parser().parse_args()
    report = build_shell_acceptance_report(
        frontend_url=args.frontend_url,
        skip_http=bool(args.skip_http),
        timeout_seconds=float(args.timeout_seconds),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.format == "pretty" else None))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
