# 桌面应用后端接口说明

## 文档目标

这份文档专门说明当前仓库里为 Windows 桌面前端预留的后端接口层。它不替代 [README.md](/C:/github/pywechat/pywechat-main/pywechat-main/README.md) 和 [docs/architecture-overview.md](/C:/github/pywechat/pywechat-main/pywechat-main/docs/architecture-overview.md)，而是聚焦回答两个问题：

1. 前端后面应该接哪一层，而不是直接接底层运行时？
2. 现在已经有哪些真功能可以调用，哪些只是占位接口？

## 当前入口

统一入口是 [wechat_ai/app/service.py](C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/app/service.py) 里的 `DesktopAppService`。

相关模块包括：

- [wechat_ai/app/models.py](C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/app/models.py)
  页面 DTO 和知识库 DTO
- [wechat_ai/app/settings_store.py](C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/app/settings_store.py)
  桌面应用设置读写
- [wechat_ai/app/knowledge_importer.py](C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/app/knowledge_importer.py)
  拖拽文件导入本地知识库并重建索引

## 已可用的真功能

### 首页

- `get_app_status()`
- `start_daemon()`
- `pause_daemon()`
- `stop_daemon()`

说明：

- 当前守护状态先保存在 `wechat_ai/data/app/daemon_state.json`
- 这还不是最终的后台守护进程控制器，但前端可以先按这个协议接状态和按钮

### 设置

- `get_settings()`
- `update_settings(patch)`

设置文件当前保存到：

- `wechat_ai/data/app/desktop_settings.json`

### 知识库

- `import_knowledge_files(paths)`
- `list_knowledge_files()`
- `get_knowledge_status()`
- `rebuild_knowledge_index()`

当前真实支持的文件类型：

- `.txt`
- `.md`
- `.json`

已预留但暂未实现真实解析器：

- `.pdf`
- `.docx`

导入后的文件会复制到：

- `wechat_ai/data/knowledge/uploads/`

索引文件位置：

- `wechat_ai/data/knowledge/local_knowledge_index.json`

## 当前是占位的接口

这些接口现在已经有稳定返回结构，但暂时不会执行真实微信操作：

- `list_conversations()`
- `get_conversation_messages(conversation_id)`
- `suggest_reply(conversation_id, message_text)`
- `send_reply(conversation_id, text)`
- `handoff_conversation(conversation_id)`

这类接口当前会返回 `not_implemented`，目的是先让前端对接字段、按钮状态和交互流，不会误发消息。

## 客户页接口

当前客户页后端复用现有 identity 模块：

- `list_customers()`
- `get_customer(customer_id)`
- `list_identity_drafts()`
- `list_identity_candidates()`

它们来自：

- [wechat_ai/identity/identity_admin.py](C:/github/pywechat/pywechat-main/pywechat-main/wechat_ai/identity/identity_admin.py)

所以客户页第一版已经能挂接：

- 已确认客户
- 待确认 draft
- 待合并 candidate

## 前端对接建议

前端第一版建议只直接依赖 `DesktopAppService`，不要直接调用：

- `wechat_runtime`
- `reply_pipeline`
- `memory_store`
- `identity_repository`

原因是这些模块仍属于内核层，后面还会继续演进，而 `DesktopAppService` 就是专门给桌面页面层准备的稳定边界。

## 调试脚本

如果你想在前端接入前先看一下这层返回的整体结构，可以运行：

```powershell
py -3 scripts\show_desktop_app_snapshot.py
```

这个脚本会输出：

- 首页状态
- 设置
- 知识库状态
- 客户列表
- draft / candidate 列表
