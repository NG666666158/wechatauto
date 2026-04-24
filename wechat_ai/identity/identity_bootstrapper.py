from __future__ import annotations

from uuid import uuid4

from .identity_models import DraftUser, IdentityRawSignal


class IdentityBootstrapper:
    def create_draft(self, signal: IdentityRawSignal) -> DraftUser:
        source_signals: list[str] = ["new_conversation_no_alias_hit"]
        current_intent = "未知"
        user_type = "未知"
        confidence = 0.35
        text = signal.text
        if any(keyword in text for keyword in ("订单", "发货", "售后", "退款", "价格", "报价")):
            current_intent = "咨询/售后"
            user_type = "客户"
            confidence = 0.55
            source_signals.append("message_contains_order_keywords")
        if any(keyword in text for keyword in ("老板", "客服", "店家")):
            source_signals.append("calls_me_business_role")
        name = signal.sender_name or signal.display_name or signal.conversation_id
        timestamp = signal.captured_at or ""
        return DraftUser(
            draft_user_id=f"draft_{uuid4().hex[:12]}",
            proposed_name=name.strip() or "未知用户",
            proposed_user_type=user_type,
            current_intent=current_intent,
            relationship_to_me="未知",
            confidence=confidence,
            source_signals=source_signals,
            conversation_id=signal.conversation_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
