from __future__ import annotations

from .models import DaemonStatus, ScheduleStatus, TrayMenuItem, TrayState


class TrayAdapter:
    def build_state(self, *, daemon_status: DaemonStatus, schedule_status: ScheduleStatus) -> TrayState:
        tooltip = f"WeChat AI: {daemon_status.state}"
        if schedule_status.enabled:
            tooltip += f" | schedule: {'run' if schedule_status.should_run else 'pause'}"
        menu_items = [
            TrayMenuItem(item_id="show", label="显示主界面", action="show_window"),
            TrayMenuItem(item_id="start", label="开始守护", action="start_daemon", enabled=daemon_status.state != "running"),
            TrayMenuItem(item_id="pause", label="暂停守护", action="pause_daemon", enabled=daemon_status.state == "running"),
            TrayMenuItem(item_id="stop", label="停止守护", action="stop_daemon", enabled=daemon_status.state != "stopped"),
            TrayMenuItem(item_id="exit", label="退出应用", action="exit_app"),
        ]
        recommended_action = "pause_daemon" if daemon_status.state == "running" else "start_daemon"
        return TrayState(tooltip=tooltip, menu_items=menu_items, recommended_action=recommended_action)
