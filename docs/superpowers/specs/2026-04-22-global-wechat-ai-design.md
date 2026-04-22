# Global WeChat AI Auto Reply Design

## Goal

Add a global polling entrypoint on top of `pyweixin` and `wechat_ai` so the app can scan unread sessions, reply to all unread direct messages, and reply to group messages only when the current user is mentioned.

## Scope

- Use `pyweixin.Messages.check_new_messages()` as the unread source.
- Process unread messages one by one in arrival order as returned by `pyweixin`.
- For direct chats, generate and send one AI reply per unread text message.
- For group chats, generate and send replies only for unread text messages that mention the current user.
- Keep dedupe minimal and in-memory for the current run only.
- Do not add persistence, batching, or delayed merge logic in this change.

## Architecture

Add a polling coordinator to `wechat_ai.wechat_runtime.WeChatAIApp`.

- The coordinator loops until a duration expires.
- Each poll calls `Messages.check_new_messages(close_weixin=False)`.
- For each unread session:
  - Open the chat window through existing `pyweixin` navigation helpers.
  - Detect whether it is a group chat with `Tools.is_group_chat(...)`.
  - Filter unread items to text messages only.
  - For direct chats, call the existing friend reply engine.
  - For group chats, reuse the existing mention detection rule and only reply when the message includes `@all` or `@<my name>`.
  - Send replies through `Messages.send_messages_to_friend(...)`.

## Error Handling

- If one session fails, continue processing the rest of the poll cycle.
- If model generation fails, fall back to the configured fallback reply.
- Ignore empty unread payloads and non-text items.

## Verification

- Unit-test the coordinator with fake `Messages`, `Navigator`, and `Tools` collaborators.
- Verify:
  - direct chats are replied to
  - group non-mention messages are ignored
  - group mention messages are replied to
  - poll loops aggregate counts and continue after per-session errors
