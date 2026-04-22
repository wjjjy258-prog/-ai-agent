# Aurora Agent Web 系统结构文档

最后更新：2026-04-21  
维护约定：每次修改系统功能（后端/前端/启动脚本/数据结构）后，都要同步更新本文件与“更新记录”。

## 1. 系统总览
- 项目类型：本地优先的 AI Agent Web 应用（FastAPI + 原生前端 JS）。
- 核心能力：
- 多会话聊天与历史持久化（SQLite）。
- 任务/笔记/计划类工具能力（命令式）。
- 技能中心（关键词触发的系统提示词注入）。
- 文件上传并注入对话上下文。
- 模型中心（本地模型切换、模型库浏览、Ollama 下载）。
- 设置中心（主题、Provider、模型参数、目录检测、端口等）。

## 2. LLM 架构
- 统一抽象：`src/ai_agent/llm.py`
- `BaseLLMClient` 统一了：
- `chat` / `chat_stream`
- `list_models`
- `list_remote_models`
- `pull_model_stream`（仅支持的 provider 可用）
- `supports_model_pull`
- 当前 provider：
- `ollama`：完整支持聊天、流式、模型库、标签、下载进度。
- `openai_compatible`：支持聊天、流式、模型列表（用于百炼等 OpenAI 兼容接口），不支持本地下载。
- `null`：LLM 关闭时使用，保留 provider/model 元数据，避免前端状态丢失。
- 性能优化：`ollama` 的模型库搜索与标签列表使用短 TTL 缓存，降低重复网络请求。

## 3. 配置与持久化
- 配置定义：`src/ai_agent/config.py`
- 关键字段：
- `llm_provider`
- `ollama_base_url` / `ollama_model`
- `openai_base_url` / `openai_model` / `openai_api_key`
- `llm_history_limit` / `intent_confidence_threshold`
- 配置存储：`app_settings` 表（`src/ai_agent/memory.py`）。
- API Key 策略：
- 后端保存明文（本地 SQLite）。
- 前端仅拿到 `openai_has_api_key` 和掩码，不返回明文 key。

## 4. Agent 运行时
- 入口：`src/ai_agent/agent.py`
- 职责：
- 读取并合并配置（环境变量 + DB 设置）。
- 构建 LLM 客户端并暴露 `runtime_metadata`。
- 处理消息：工具路由优先，LLM 兜底。
- 提供运行时设置更新：provider 切换、模型切换、阈值更新、目录更新。
- 模型默认值持久化策略：
- 通用键：`default_model`
- 分 provider 键：`default_model_ollama`、`default_model_openai_compatible`

## 5. Web API 结构
- 文件：`src/ai_agent/web/app.py`
- 系统操作模块：`src/ai_agent/web/system_ops.py`（Ollama 可达性检测、自动启动、Windows 目录选择器）。
- 核心接口：
- `GET /api/runtime`
- `GET/PUT /api/settings`
- `GET /api/models`
- `GET /api/model-library`
- `GET /api/model-library/{family}/tags`
- `POST /api/models/select`
- `POST /api/models/pull`（NDJSON 流）
- `POST /api/ollama/start`（尝试自动启动本机 Ollama）
- `GET /api/ollama/version`（查询本机可执行版本 + 服务版本）
- `POST /api/uploads` / `DELETE /api/uploads/{id}`
- `/api/conversations*`、`/api/skills*`
- 静态资源响应头统一禁用缓存，避免更新后前端页面仍显示旧版本。

## 6. 前端结构
- 文件：
- `src/ai_agent/web/static/index.html`
- `src/ai_agent/web/static/styles.css`
- `src/ai_agent/web/static/app.js`
- 关键模块：
- 侧边栏：会话历史与收起展开。
- 主聊天区：消息流式渲染、上传附件、模型切换。
- 工作台弹窗：模型中心 / 技能中心 / 设置中心。
- 交互兜底：关键异步按钮统一补齐 `try/catch`，失败会给出可见反馈，避免“点击无反应”。
- 设置中心新增 provider 逻辑：
- `ollama`：显示 Ollama 地址与模型目录检测区块。
- `openai_compatible`：显示 API Base URL / API Key / API 模型配置区块。

## 7. 启动脚本
- 文件：`start_aurora_web.bat`
- 功能：
- 自动创建 `.venv` 并安装依赖。
- 自动端口探测（避免 8000 被占用直接失败），并增加端口值鲁棒清洗（防空格/异常值）。
- 按 provider 执行启动前检查：
- `ollama`：检查 `AURORA_OLLAMA_BASE_URL/api/tags`
- 其他 provider：跳过本地 Ollama 检查
- 当 provider 为 `ollama` 且不可达时，默认会自动尝试拉起 Ollama（`AURORA_AUTO_START_OLLAMA=1`）。
- 启动浏览器改为后台健康检查后再打开，降低“先看到旧页面/空白页”的概率。

## 8. 测试
- 目录：`tests/`
- 覆盖：
- Agent 基础流程
- 聊天与存储
- 技能
- 工具
- Web API（含设置、上传、模型接口）
- 新增验证：
- OpenAI 兼容 provider 设置保存与 runtime 生效
- Ollama 模型库与标签缓存行为（`tests/test_llm_cache.py`）
- `GET /api/ollama/version` 返回结构验证（`tests/test_web_api.py`）

## 9. 更新记录
- 2026-04-21
- 新增多 Provider 架构：`ollama` + `openai_compatible`。
- 新增 OpenAI 兼容客户端，支持 API 对话与流式返回（适配百炼兼容接口）。
- 设置中心新增 provider、API Base URL、API Key、API 默认模型配置。
- API Key 改为后端安全返回（仅状态/掩码，不返回明文）。
- 模型默认值改为按 provider 分别持久化。
- 启动脚本改为按 provider 检查服务，不再强依赖 Ollama 提示。
- 前端模型中心增加 provider 能力判断：不支持下载时自动切换为“设为默认”交互。
- 新增 `POST /api/ollama/start`，支持在设置页一键启动 Ollama。
- 启动脚本新增自动拉起 Ollama 逻辑（provider=ollama 时）。
- “查看版本”交互增加错误提示，后端标签接口增加本地已下载标签回退逻辑。
- 设置接口新增 provider 严格校验：无效 provider 不再静默降级，直接返回 400。
- 标签版本接口限定为 Ollama provider，非 Ollama 会返回明确提示，避免“点了没反应”。
- `web/app.py` 的系统级逻辑已下沉到 `web/system_ops.py`，主文件职责更聚焦 API 路由。
- 新增 `tests/test_llm_cache.py`，验证模型库/标签缓存逻辑。
- 新增 `GET /api/ollama/version`，前端设置页可一键查看“本机版本 + 服务连通状态”。
- 模型中心交互补强：`查看版本` 增加加载态与结果提示；Ollama 未连接时下载/切换给出明确引导。
- 前端关键点击统一增加错误反馈兜底，减少静默失败。
- Web 层新增静态资源禁缓存响应头，避免更新后浏览器继续显示旧 JS/CSS。
- 启动脚本加强：端口环境变量清洗、旧进程匹配范围扩展、浏览器改为健康检查后打开。
