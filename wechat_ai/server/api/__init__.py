from .controls import router as controls_router
from .conversations import router as conversations_router
from .customers import router as customers_router
from .dashboard import router as dashboard_router
from .environment import router as environment_router
from .errors import router as errors_router
from .health import router as health_router
from .identity import router as identity_router
from .knowledge import router as knowledge_router
from .logs import router as logs_router
from .ping import router as ping_router
from .privacy import router as privacy_router
from .runtime import router as runtime_router
from .settings import router as settings_router

__all__ = [
    "customers_router",
    "controls_router",
    "conversations_router",
    "dashboard_router",
    "environment_router",
    "errors_router",
    "health_router",
    "identity_router",
    "knowledge_router",
    "logs_router",
    "ping_router",
    "privacy_router",
    "runtime_router",
    "settings_router",
]
