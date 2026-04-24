from __future__ import annotations

from .errors import ErrorCode


HTTP_ERROR_CATALOG: tuple[dict[str, object], ...] = (
    {
        "code": ErrorCode.REQUEST_INVALID.value,
        "http_status": 422,
        "message": "Invalid request",
        "description": "请求体、查询参数或路径参数不符合 API 契约。",
    },
    {
        "code": ErrorCode.CONFIG_INVALID.value,
        "http_status": 400,
        "message": "Configuration invalid",
        "description": "启动模式、配置项或运行参数不被当前后端支持。",
    },
    {
        "code": ErrorCode.RUNTIME_ALREADY_RUNNING.value,
        "http_status": 409,
        "message": "Runtime already running",
        "description": "守护进程已经在运行，重复启动会被拒绝。",
    },
    {
        "code": ErrorCode.RUNTIME_NOT_RUNNING.value,
        "http_status": 409,
        "message": "Runtime not running",
        "description": "守护进程未运行时执行停止操作会被拒绝。",
    },
    {
        "code": ErrorCode.WECHAT_WINDOW_NOT_FOUND.value,
        "http_status": 503,
        "message": "WeChat window not found",
        "description": "未发现可操作的微信窗口或窗口不可访问。",
    },
    {
        "code": ErrorCode.WECHAT_NOT_LOGIN.value,
        "http_status": 503,
        "message": "WeChat not logged in",
        "description": "微信未登录或主界面尚未就绪。",
    },
    {
        "code": ErrorCode.KNOWLEDGE_INDEX_MISSING.value,
        "http_status": 409,
        "message": "Knowledge index missing",
        "description": "知识库索引尚未构建，不能执行依赖索引的能力。",
    },
    {
        "code": ErrorCode.MODEL_API_FAILED.value,
        "http_status": 502,
        "message": "Model API failed",
        "description": "模型服务调用失败或返回不可用结果。",
    },
    {
        "code": ErrorCode.PERMISSION_DENIED.value,
        "http_status": 403,
        "message": "Permission denied",
        "description": "当前操作缺少必要权限或被安全策略拒绝。",
    },
    {
        "code": ErrorCode.UNKNOWN_ERROR.value,
        "http_status": 500,
        "message": "Internal server error",
        "description": "未预期的后端异常，响应中不会暴露敏感堆栈细节。",
    },
)


SEND_REPLY_STATUSES: tuple[dict[str, object], ...] = (
    {"status": "blocked", "http_status": 200, "description": "发送前校验未通过，前端应展示原因但不视为 API 崩溃。"},
    {"status": "not_implemented", "http_status": 200, "description": "真实发送器未启用，后端仅完成校验和占位返回。"},
    {"status": "sent", "http_status": 200, "description": "消息已发送，必要时也已通过视觉确认。"},
    {"status": "unconfirmed", "http_status": 200, "description": "发送动作已执行，但窗口侧未确认消息出现。"},
    {"status": "failed", "http_status": 200, "description": "真实发送动作失败，错误留在 data.reason / data.reason_code。"},
)


SEND_REPLY_REASON_CODES: tuple[dict[str, str], ...] = (
    {"code": "EMPTY_TEXT", "status": "blocked", "description": "回复内容为空。"},
    {"code": "HUMAN_TAKEOVER", "status": "blocked", "description": "会话已由人工接管。"},
    {"code": "CONVERSATION_PAUSED", "status": "blocked", "description": "会话已暂停自动回复。"},
    {"code": "BLACKLISTED", "status": "blocked", "description": "会话在黑名单中。"},
    {"code": "SEND_FAILED", "status": "failed", "description": "真实发送器执行失败。"},
    {"code": "SEND_NOT_CONFIRMED", "status": "unconfirmed", "description": "发送后未通过窗口侧确认。"},
)


def error_catalog() -> dict[str, object]:
    return {
        "http_errors": [dict(item) for item in HTTP_ERROR_CATALOG],
        "send_reply_statuses": [dict(item) for item in SEND_REPLY_STATUSES],
        "send_reply_reason_codes": [dict(item) for item in SEND_REPLY_REASON_CODES],
    }
