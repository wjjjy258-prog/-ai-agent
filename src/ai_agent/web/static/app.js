const ZH = {
  justNow: "刚刚",
  minAgo: "分钟前",
  hourAgo: "小时前",
  dayAgo: "天前",
  requestFailed: "请求失败",
  assistant: "助手",
  you: "你",
  thinking: "思考中...",
  noMessage: "当前对话暂无消息，发送第一条消息开始吧。",
  noChat: "暂无历史对话",
  emptyChat: "空对话",
  messageUnit: "条消息",
  rename: "重命名",
  remove: "删除",
  renamePrompt: "请输入新标题",
  deleteConfirm: "确认删除该对话？",
  runtimeLoading: "运行时加载中...",
  connected: "已连接",
  disconnected: "未连接",
  unavailableModel: "（不可用）",
  noModel: "无可用模型",
  initFailed: "初始化失败：",
  streamUnsupported: "浏览器不支持流式读取。",
  modelEmpty: "模型没有返回内容，请重试。",
  newChat: "新对话",
  noSkills: "还没有自定义技能，你可以先创建一个。",
  noRemoteModels: "没有找到匹配的模型，可以换个关键词试试。",
  noLocalModels: "当前还没有可切换的本地模型。",
  noTags: "没有找到该模型的标签信息。",
  noDetection: "暂未检测到模型目录。",
  settingsSaved: "设置已保存。模型目录变更后如未生效，请重启 Ollama。",
  detectingModels: "正在检测本机模型目录，请稍候...",
  detectDone: "检测完成。你可以在候选目录中一键套用。",
  pickingDir: "正在打开文件夹选择器...",
  pickCanceled: "已取消选择文件夹。",
  pickDone: "已设置模型目录：",
  pullStarted: "开始下载",
  pullWaiting: "正在等待模型服务返回进度...",
  uploadTooMany: "一次最多上传 5 个文件。",
  uploadPicking: "正在上传文件...",
  uploadFailed: "文件上传失败",
  uploadEmpty: "请先选择文件。",
  uploadListTitle: "已附加文件",
  providerNoPull: "当前提供方不支持本地下载模型，请在设置中切换到 Ollama。",
  openaiKeyConfigured: "API Key：已配置（安全起见不显示明文）",
  openaiKeyMissing: "API Key：未配置",
  settingsSavedNoRestart: "设置已保存。",
  startingOllama: "正在尝试启动 Ollama，请稍候...",
  startOllamaOk: "Ollama 已就绪。",
  startOllamaFail: "自动启动 Ollama 失败，请确认本机已安装 Ollama。",
  checkingVersion: "正在检查 Ollama 版本...",
  versionUnavailable: "未检测到 Ollama 可执行程序，请先安装 Ollama。",
  loadingTags: "正在加载标签版本...",
  tagsLoaded: "标签版本加载完成。",
  modelSetDone: "默认模型已更新为",
  modelSetPendingOllama: "Ollama 未连接，模型会在服务可用后生效。",
  ollamaNotReachable: "当前无法连接 Ollama，请先点击“启动 Ollama”或手动启动后再试。",
  actionFailed: "操作失败",
};

const state = {
  conversations: [],
  activeConversationId: null,
  sending: false,
  runtime: null,
  selectedModel: "",
  inspectorOpen: false,
  inspectorTab: "models",
  remoteQuery: "",
  remoteModels: [],
  activeModelFamily: "",
  modelTags: [],
  pulling: false,
  skills: [],
  editingSkillId: null,
  sidebarCollapsed: false,
  pendingUploads: [],
  uploadBusy: false,
  settings: {
    theme: "amber",
    llm_provider: "ollama",
    llm_model: "",
    ollama_model: "qwen3.5:4b",
    ollama_models_dir: "",
    ollama_base_url: "http://127.0.0.1:11434",
    openai_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    openai_model: "qwen-plus",
    openai_has_api_key: false,
    openai_api_key_masked: "",
    llm_history_limit: 20,
    intent_confidence_threshold: 0.72,
    auto_select_after_pull: true,
    enter_to_send: true,
    web_port_preferred: 8000,
  },
  modelFolderDetection: {
    active_path: "",
    active_source: "default",
    items: [],
    note: "",
  },
};

const dom = {
  htmlRoot: document.documentElement,
  appShell: document.querySelector(".app-shell"),
  sidebar: document.getElementById("sidebar"),
  conversationList: document.getElementById("conversation-list"),
  messageList: document.getElementById("message-list"),
  newChatBtn: document.getElementById("new-chat-btn"),
  composerInput: document.getElementById("composer-input"),
  sendBtn: document.getElementById("send-btn"),
  uploadFileBtn: document.getElementById("upload-file-btn"),
  uploadFileInput: document.getElementById("upload-file-input"),
  uploadList: document.getElementById("upload-list"),
  template: document.getElementById("message-template"),
  subtitle: document.getElementById("chat-subtitle"),
  modelChip: document.getElementById("model-chip"),
  modelSelect: document.getElementById("model-select"),
  mobileOpenBtn: document.getElementById("mobile-open-btn"),
  mobileCloseBtn: document.getElementById("mobile-close-btn"),
  toggleHistoryBtn: document.getElementById("toggle-history-btn"),
  expandHistoryBtn: document.getElementById("expand-history-btn"),
  inspector: document.getElementById("inspector"),
  inspectorTitle: document.getElementById("inspector-title"),
  openModelCenterBtn: document.getElementById("open-model-center-btn"),
  openSkillCenterBtn: document.getElementById("open-skill-center-btn"),
  openSettingsCenterBtn: document.getElementById("open-settings-center-btn"),
  closeInspectorBtn: document.getElementById("close-inspector-btn"),
  tabModelsBtn: document.getElementById("tab-models-btn"),
  tabSkillsBtn: document.getElementById("tab-skills-btn"),
  tabSettingsBtn: document.getElementById("tab-settings-btn"),
  panelModels: document.getElementById("panel-models"),
  panelSkills: document.getElementById("panel-skills"),
  panelSettings: document.getElementById("panel-settings"),
  modelSearchInput: document.getElementById("model-search-input"),
  modelSearchBtn: document.getElementById("model-search-btn"),
  manualModelInput: document.getElementById("manual-model-input"),
  manualModelPullBtn: document.getElementById("manual-model-pull-btn"),
  modelPullProgressWrap: document.getElementById("model-pull-progress-wrap"),
  modelPullProgressFill: document.getElementById("model-pull-progress-fill"),
  modelPullProgressText: document.getElementById("model-pull-progress-text"),
  modelPullStatus: document.getElementById("model-pull-status"),
  localModelList: document.getElementById("local-model-list"),
  remoteModelList: document.getElementById("remote-model-list"),
  modelTagsSection: document.getElementById("model-tags-section"),
  modelTagsTitle: document.getElementById("model-tags-title"),
  modelTagList: document.getElementById("model-tag-list"),
  skillForm: document.getElementById("skill-form"),
  skillIdInput: document.getElementById("skill-id-input"),
  skillNameInput: document.getElementById("skill-name-input"),
  skillDescriptionInput: document.getElementById("skill-description-input"),
  skillKeywordsInput: document.getElementById("skill-keywords-input"),
  skillInstructionInput: document.getElementById("skill-instruction-input"),
  skillEnabledInput: document.getElementById("skill-enabled-input"),
  skillFormResetBtn: document.getElementById("skill-form-reset-btn"),
  skillList: document.getElementById("skill-list"),
  settingsForm: document.getElementById("settings-form"),
  settingsThemeSelect: document.getElementById("settings-theme-select"),
  settingsProviderSelect: document.getElementById("settings-provider-select"),
  settingsLlmModelInput: document.getElementById("settings-llm-model-input"),
  settingsModelDirInput: document.getElementById("settings-model-dir-input"),
  settingsPickDirBtn: document.getElementById("settings-pick-dir-btn"),
  settingsDetectBtn: document.getElementById("settings-detect-btn"),
  settingsDetectionList: document.getElementById("settings-detection-list"),
  settingsModelDirBlock: document.getElementById("settings-model-dir-block"),
  settingsOllamaUrlWrap: document.getElementById("settings-ollama-url-wrap"),
  settingsOllamaActionsWrap: document.getElementById("settings-ollama-actions-wrap"),
  settingsOllamaUrlInput: document.getElementById("settings-ollama-url-input"),
  settingsStartOllamaBtn: document.getElementById("settings-start-ollama-btn"),
  settingsOllamaVersionBtn: document.getElementById("settings-ollama-version-btn"),
  settingsOpenaiFields: document.getElementById("settings-openai-fields"),
  settingsOpenaiBaseUrlInput: document.getElementById("settings-openai-base-url-input"),
  settingsOpenaiApiKeyInput: document.getElementById("settings-openai-api-key-input"),
  settingsOpenaiClearKeyInput: document.getElementById("settings-openai-clear-key-input"),
  settingsOpenaiKeyStatus: document.getElementById("settings-openai-key-status"),
  settingsOpenaiModelInput: document.getElementById("settings-openai-model-input"),
  settingsHistoryLimitInput: document.getElementById("settings-history-limit-input"),
  settingsIntentThresholdInput: document.getElementById("settings-intent-threshold-input"),
  settingsAutoSelectInput: document.getElementById("settings-auto-select-input"),
  settingsEnterSendInput: document.getElementById("settings-enter-send-input"),
  settingsWebPortInput: document.getElementById("settings-web-port-input"),
  settingsStatus: document.getElementById("settings-status"),
};

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderMarkdownLite(text) {
  const sections = String(text).split("```");
  return sections
    .map((chunk, index) => {
      if (index % 2 === 1) {
        return `<pre><code>${escapeHtml(chunk.trim())}</code></pre>`;
      }
      const inline = escapeHtml(chunk).replace(/`([^`\n]+)`/g, "<code>$1</code>");
      return inline.replaceAll("\n", "<br>");
    })
    .join("");
}

function relativeTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diffMs < minute) return ZH.justNow;
  if (diffMs < hour) return `${Math.floor(diffMs / minute)} ${ZH.minAgo}`;
  if (diffMs < day) return `${Math.floor(diffMs / hour)} ${ZH.hourAgo}`;
  return `${Math.floor(diffMs / day)} ${ZH.dayAgo}`;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  const digits = size >= 10 || index === 0 ? 0 : 1;
  return `${size.toFixed(digits)} ${units[index]}`;
}

function setTheme(theme) {
  const safeTheme = ["amber", "ocean", "graphite"].includes(theme) ? theme : "amber";
  dom.htmlRoot.setAttribute("data-theme", safeTheme);
}

function isOllamaProvider(provider = null) {
  const target = String(provider || state.settings.llm_provider || state.runtime?.provider || "ollama").toLowerCase();
  return target === "ollama";
}

function setSettingsStatus(message, isError = false) {
  dom.settingsStatus.classList.remove("hidden");
  dom.settingsStatus.textContent = message;
  dom.settingsStatus.style.borderColor = isError ? "rgba(172, 63, 25, 0.32)" : "rgba(31, 41, 55, 0.08)";
}

function clearSettingsStatus() {
  dom.settingsStatus.classList.add("hidden");
  dom.settingsStatus.textContent = "";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || ZH.requestFailed;
    throw new Error(detail);
  }
  return payload;
}

function errorMessage(error, fallback = ZH.requestFailed) {
  if (!error) return fallback;
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message || fallback;
  return String(error);
}

function setModelActionError(error, prefix = ZH.actionFailed) {
  const detail = errorMessage(error, ZH.requestFailed);
  setPullStatus(`${prefix}：${detail}`, true);
}

function ensureOllamaReachableForModelOps(actionLabel = "该操作") {
  if (!isOllamaProvider(state.runtime?.provider)) return true;
  if (state.runtime?.reachable) return true;
  setPullStatus(`${actionLabel}需要本地 Ollama 服务在线。${ZH.ollamaNotReachable}`, true);
  setPullProgress({
    text: ZH.ollamaNotReachable,
    isError: true,
  });
  return false;
}

function syncModelConnectionHint() {
  if (!isOllamaProvider(state.runtime?.provider)) {
    return;
  }
  if (!state.runtime?.reachable) {
    setPullStatus(`Ollama 状态：未连接。${ZH.ollamaNotReachable}`, true);
    return;
  }
  if ((dom.modelPullStatus?.textContent || "").includes("Ollama 状态：未连接")) {
    clearPullStatus();
    clearPullProgress();
  }
}

function clearMessages() {
  dom.messageList.innerHTML = "";
}

function scrollToBottom() {
  dom.messageList.scrollTop = dom.messageList.scrollHeight;
}

function createMessageElement(role, content) {
  const clone = dom.template.content.cloneNode(true);
  const article = clone.querySelector(".message");
  const roleNode = clone.querySelector(".message-role");
  const bubble = clone.querySelector(".message-bubble");
  article.classList.add(role);
  roleNode.textContent = role === "assistant" ? ZH.assistant : ZH.you;
  bubble.innerHTML = renderMarkdownLite(content);
  return { article, bubble };
}

function appendMessage(role, content) {
  const { article } = createMessageElement(role, content);
  dom.messageList.appendChild(article);
  scrollToBottom();
}

function appendTypingMessage() {
  const clone = dom.template.content.cloneNode(true);
  const article = clone.querySelector(".message");
  const roleNode = clone.querySelector(".message-role");
  const bubble = clone.querySelector(".message-bubble");
  article.classList.add("assistant");
  roleNode.textContent = ZH.assistant;
  bubble.textContent = ZH.thinking;
  dom.messageList.appendChild(article);
  scrollToBottom();
  return bubble;
}

function renderEmptyState() {
  clearMessages();
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = ZH.noMessage;
  dom.messageList.appendChild(empty);
}

function renderMessages(messages) {
  clearMessages();
  if (!messages.length) {
    renderEmptyState();
    return;
  }
  for (const item of messages) {
    appendMessage(item.role, item.content);
  }
}

function truncate(text, max = 56) {
  if (!text) return "";
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

function renderConversations() {
  dom.conversationList.innerHTML = "";
  if (!state.conversations.length) {
    const empty = document.createElement("div");
    empty.className = "conversation-meta";
    empty.textContent = ZH.noChat;
    dom.conversationList.appendChild(empty);
    return;
  }

  for (const convo of state.conversations) {
    const item = document.createElement("div");
    item.className = "conversation-item";
    if (state.activeConversationId === convo.id) {
      item.classList.add("active");
    }
    item.dataset.id = convo.id;
    item.innerHTML = `
      <h3 class="conversation-title">${escapeHtml(truncate(convo.title, 38))}</h3>
      <div class="conversation-meta">${escapeHtml(truncate(convo.last_message_preview || ZH.emptyChat, 62))}</div>
      <div class="conversation-meta">${convo.message_count} ${ZH.messageUnit} · ${relativeTime(convo.updated_at)}</div>
      <div class="conversation-actions">
        <button data-action="rename">${ZH.rename}</button>
        <button data-action="delete">${ZH.remove}</button>
      </div>
    `;
    item.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLButtonElement) return;
      selectConversation(convo.id).catch((error) => {
        window.alert(errorMessage(error, ZH.requestFailed));
      });
    });
    item.querySelector("[data-action='rename']").addEventListener("click", async (event) => {
      event.stopPropagation();
      try {
        const title = window.prompt(ZH.renamePrompt, convo.title);
        if (!title || !title.trim()) return;
        await api(`/api/conversations/${convo.id}`, {
          method: "PATCH",
          body: JSON.stringify({ title: title.trim() }),
        });
        await loadConversations();
      } catch (error) {
        window.alert(errorMessage(error, ZH.requestFailed));
      }
    });
    item.querySelector("[data-action='delete']").addEventListener("click", async (event) => {
      event.stopPropagation();
      try {
        const ok = window.confirm(ZH.deleteConfirm);
        if (!ok) return;
        await api(`/api/conversations/${convo.id}`, { method: "DELETE" });
        if (state.activeConversationId === convo.id) {
          state.activeConversationId = null;
        }
        await loadConversations();
        if (!state.activeConversationId && state.conversations.length) {
          await selectConversation(state.conversations[0].id);
        } else if (!state.conversations.length) {
          renderEmptyState();
        }
      } catch (error) {
        window.alert(errorMessage(error, ZH.requestFailed));
      }
    });
    dom.conversationList.appendChild(item);
  }
}

function updateModelChip() {
  if (!state.runtime) {
    dom.modelChip.textContent = ZH.runtimeLoading;
    return;
  }
  const runtime = state.runtime;
  const provider = runtime.provider === "openai_compatible" ? "API" : (runtime.provider || "none").toUpperCase();
  const model = runtime.model || "N/A";
  const reachable = runtime.reachable ? ZH.connected : ZH.disconnected;
  dom.modelChip.textContent = `${provider} · ${model} · ${reachable} · ${runtime.enabled_skills || 0} 技能`;
}

function renderModelOptions(models, currentModel) {
  dom.modelSelect.innerHTML = "";
  const items = Array.isArray(models) ? models : [];
  if (!items.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = currentModel ? `${currentModel}${ZH.unavailableModel}` : ZH.noModel;
    dom.modelSelect.appendChild(option);
    dom.modelSelect.disabled = true;
    state.selectedModel = "";
    return;
  }

  for (const modelName of items) {
    const option = document.createElement("option");
    option.value = modelName;
    option.textContent = modelName;
    if (modelName === currentModel) {
      option.selected = true;
    }
    dom.modelSelect.appendChild(option);
  }
  dom.modelSelect.disabled = false;
  state.selectedModel = dom.modelSelect.value || currentModel || items[0];
}

function renderLocalModels() {
  dom.localModelList.innerHTML = "";
  const models = state.runtime?.available_models || [];
  if (!models.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = ZH.noLocalModels;
    dom.localModelList.appendChild(empty);
    return;
  }

  for (const modelName of models) {
    const card = document.createElement("div");
    card.className = "entity-card";
    const isSelected = state.runtime?.model === modelName;
    card.innerHTML = `
      <div class="entity-head">
        <div>
          <h4 class="entity-title">${escapeHtml(modelName)}</h4>
          <p class="entity-subtitle">${isSelected ? "当前默认模型" : "已下载，可直接切换"}</p>
        </div>
        <div class="entity-tags">
          <span class="entity-chip ${isSelected ? "active" : ""}">${isSelected ? "当前使用" : "本地模型"}</span>
        </div>
      </div>
      <div class="entity-actions">
        <button class="secondary-btn" data-action="select">${isSelected ? "已选中" : "切换为默认"}</button>
      </div>
    `;
    card.querySelector("[data-action='select']").disabled = isSelected;
    card.querySelector("[data-action='select']").addEventListener("click", async () => {
      try {
        await selectDefaultModel(modelName);
      } catch (error) {
        setModelActionError(error, "切换模型失败");
      }
    });
    dom.localModelList.appendChild(card);
  }
}

function createMetaChips(values, className = "entity-chip") {
  return values.map((value) => `<span class="${className}">${escapeHtml(value)}</span>`).join("");
}

function renderRemoteModels() {
  dom.remoteModelList.innerHTML = "";
  if (!state.remoteModels.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = ZH.noRemoteModels;
    dom.remoteModelList.appendChild(empty);
    return;
  }

  const canPull = !!state.runtime?.supports_model_pull && isOllamaProvider(state.runtime?.provider);
  const ollamaReachable = !!state.runtime?.reachable;
  for (const item of state.remoteModels) {
    const card = document.createElement("div");
    card.className = "entity-card";
    const capabilities = item.capabilities || [];
    const sizes = item.sizes || [];
    const chips = [...capabilities, ...sizes].slice(0, 8);
    card.innerHTML = `
      <div class="entity-head">
        <div>
          <h4 class="entity-title">${escapeHtml(item.name)}</h4>
          <p class="entity-subtitle">${escapeHtml(item.description || "暂无描述")}</p>
        </div>
        <div class="entity-tags">
          ${item.has_downloaded_variant ? '<span class="entity-chip active">已有本地版本</span>' : ""}
        </div>
      </div>
      <div class="entity-meta">
        ${item.pull_count ? `<span class="entity-chip">${escapeHtml(item.pull_count)} 次下载</span>` : ""}
        ${item.tag_count ? `<span class="entity-chip">${escapeHtml(item.tag_count)} 个标签</span>` : ""}
        ${item.updated ? `<span class="entity-chip">更新于 ${escapeHtml(item.updated)}</span>` : ""}
      </div>
      <div class="entity-tags">${createMetaChips(chips)}</div>
      <div class="entity-actions">
        ${canPull ? '<button class="secondary-btn" data-action="view-tags">查看版本</button>' : ""}
        ${canPull ? '<button class="secondary-btn" data-action="pull-latest">下载最新版</button>' : '<button class="secondary-btn" data-action="select-default">切换为默认</button>'}
      </div>
    `;
    if (canPull) {
      const viewTagsBtn = card.querySelector("[data-action='view-tags']");
      const pullLatestBtn = card.querySelector("[data-action='pull-latest']");
      viewTagsBtn.addEventListener("click", async () => {
        const oldText = viewTagsBtn.textContent;
        viewTagsBtn.disabled = true;
        viewTagsBtn.textContent = "加载中...";
        try {
          setPullStatus(ZH.loadingTags);
          clearPullProgress();
          await loadModelTags(item.family || item.name);
          setPullStatus(`${ZH.tagsLoaded}（${state.modelTags.length} 个）`);
          if (dom.modelTagsSection && !dom.modelTagsSection.classList.contains("hidden")) {
            dom.modelTagsSection.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        } catch (error) {
          setModelActionError(error, "加载标签版本失败");
        } finally {
          viewTagsBtn.disabled = false;
          viewTagsBtn.textContent = oldText || "查看版本";
        }
      });
      pullLatestBtn.addEventListener("click", async () => {
        if (!ollamaReachable) {
          ensureOllamaReachableForModelOps("下载模型");
          return;
        }
        try {
          await pullModel(item.family || item.name, state.settings.auto_select_after_pull !== false);
        } catch (error) {
          setModelActionError(error, "下载模型失败");
        }
      });
    } else {
      card.querySelector("[data-action='select-default']").addEventListener("click", async () => {
        try {
          await selectDefaultModel(item.name || item.family);
        } catch (error) {
          setModelActionError(error, "切换模型失败");
        }
      });
    }
    dom.remoteModelList.appendChild(card);
  }
}

function renderModelTags() {
  dom.modelTagList.innerHTML = "";
  if (!isOllamaProvider(state.runtime?.provider)) {
    dom.modelTagsSection.classList.add("hidden");
    return;
  }
  if (!state.activeModelFamily) {
    dom.modelTagsSection.classList.add("hidden");
    return;
  }
  dom.modelTagsSection.classList.remove("hidden");
  dom.modelTagsTitle.textContent = `${state.activeModelFamily} · 标签版本`;

  if (!state.modelTags.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = ZH.noTags;
    dom.modelTagList.appendChild(empty);
    return;
  }

  for (const item of state.modelTags) {
    const card = document.createElement("div");
    card.className = "entity-card";
    card.innerHTML = `
      <div class="entity-head">
        <div>
          <h4 class="entity-title">${escapeHtml(item.name)}</h4>
          <p class="entity-subtitle">${item.downloaded ? "已经下载，可以直接切换。" : "未下载，点击后会自动拉取并切换。"}</p>
        </div>
        <div class="entity-tags">
          ${item.selected ? '<span class="entity-chip active">当前默认</span>' : ""}
          ${item.downloaded ? '<span class="entity-chip">已下载</span>' : '<span class="entity-chip">未下载</span>'}
        </div>
      </div>
      <div class="entity-actions">
        <button class="secondary-btn" data-action="activate">${item.downloaded ? "切换到此模型" : "下载并切换"}</button>
      </div>
    `;
    card.querySelector("[data-action='activate']").addEventListener("click", async () => {
      try {
        if (item.downloaded) {
          await selectDefaultModel(item.name);
        } else {
          if (!ensureOllamaReachableForModelOps("下载并切换模型")) {
            return;
          }
          await pullModel(item.name, state.settings.auto_select_after_pull !== false);
        }
      } catch (error) {
        setModelActionError(error, "处理模型版本失败");
      }
    });
    dom.modelTagList.appendChild(card);
  }
}

function updateModelCenterCapabilities() {
  const canPull = !!state.runtime?.supports_model_pull && isOllamaProvider(state.runtime?.provider);
  const reachable = !!state.runtime?.reachable;
  if (dom.manualModelPullBtn) {
    dom.manualModelPullBtn.textContent = canPull ? (reachable ? "下载并切换" : "先启动 Ollama") : "设为默认";
    dom.manualModelPullBtn.disabled = state.pulling;
  }
  if (dom.manualModelInput) {
    if (canPull && reachable) {
      dom.manualModelInput.placeholder = "或直接输入模型名，例如 qwen3.5:7b";
    } else if (canPull && !reachable) {
      dom.manualModelInput.placeholder = "Ollama 未连接，请先在设置中启动";
    } else {
      dom.manualModelInput.placeholder = "输入可用模型名，例如 qwen-plus";
    }
  }
}

function skillKeywordsToText(skill) {
  return Array.isArray(skill.trigger_keywords) ? skill.trigger_keywords.join(", ") : "";
}

function renderSkills() {
  dom.skillList.innerHTML = "";
  if (!state.skills.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = ZH.noSkills;
    dom.skillList.appendChild(empty);
    return;
  }

  for (const skill of state.skills) {
    const card = document.createElement("div");
    card.className = "entity-card";
    const keywordText = skillKeywordsToText(skill);
    card.innerHTML = `
      <div class="entity-head">
        <div>
          <h4 class="entity-title">${escapeHtml(skill.name)}</h4>
          <p class="entity-subtitle">${escapeHtml(skill.description || "暂无简介")}</p>
        </div>
        <div class="entity-tags">
          <span class="entity-chip ${skill.enabled ? "active" : ""}">${skill.enabled ? "启用中" : "已停用"}</span>
        </div>
      </div>
      <div class="entity-meta">
        <span class="entity-chip">关键词：${escapeHtml(keywordText || "留空则始终生效")}</span>
      </div>
      <div class="entity-subtitle">${escapeHtml(truncate(skill.instruction, 160))}</div>
      <div class="entity-actions">
        <button class="secondary-btn" data-action="toggle">${skill.enabled ? "停用" : "启用"}</button>
        <button class="secondary-btn" data-action="edit">编辑</button>
        <button class="secondary-btn" data-action="delete">删除</button>
      </div>
    `;
    card.querySelector("[data-action='toggle']").addEventListener("click", async () => {
      try {
        await toggleSkill(skill.id, !skill.enabled);
      } catch (error) {
        window.alert(errorMessage(error, ZH.requestFailed));
      }
    });
    card.querySelector("[data-action='edit']").addEventListener("click", () => {
      populateSkillForm(skill);
      openInspector("skills");
    });
    card.querySelector("[data-action='delete']").addEventListener("click", async () => {
      try {
        const ok = window.confirm(`确认删除技能“${skill.name}”？`);
        if (!ok) return;
        await api(`/api/skills/${skill.id}`, { method: "DELETE" });
        if (state.editingSkillId === skill.id) {
          resetSkillForm();
        }
        await loadSkills();
        await loadRuntime();
      } catch (error) {
        window.alert(errorMessage(error, ZH.requestFailed));
      }
    });
    dom.skillList.appendChild(card);
  }
}

function populateSkillForm(skill) {
  state.editingSkillId = skill.id;
  dom.skillIdInput.value = skill.id;
  dom.skillNameInput.value = skill.name || "";
  dom.skillDescriptionInput.value = skill.description || "";
  dom.skillKeywordsInput.value = skillKeywordsToText(skill);
  dom.skillInstructionInput.value = skill.instruction || "";
  dom.skillEnabledInput.checked = !!skill.enabled;
}

function resetSkillForm() {
  state.editingSkillId = null;
  dom.skillIdInput.value = "";
  dom.skillNameInput.value = "";
  dom.skillDescriptionInput.value = "";
  dom.skillKeywordsInput.value = "";
  dom.skillInstructionInput.value = "";
  dom.skillEnabledInput.checked = true;
}

function setPullStatus(message, isError = false) {
  dom.modelPullStatus.classList.remove("hidden");
  dom.modelPullStatus.textContent = message;
  dom.modelPullStatus.style.borderColor = isError ? "rgba(172, 63, 25, 0.32)" : "rgba(31, 41, 55, 0.08)";
}

function clearPullStatus() {
  dom.modelPullStatus.classList.add("hidden");
  dom.modelPullStatus.textContent = "";
}

function setPullProgress({ percent = null, text = "", isError = false, indeterminate = false } = {}) {
  if (!dom.modelPullProgressWrap || !dom.modelPullProgressFill || !dom.modelPullProgressText) {
    return;
  }

  dom.modelPullProgressWrap.classList.remove("hidden");
  dom.modelPullProgressText.textContent = text || ZH.pullWaiting;

  dom.modelPullProgressFill.classList.remove("indeterminate", "error");
  if (isError) {
    dom.modelPullProgressFill.classList.add("error");
    dom.modelPullProgressFill.style.width = "100%";
    return;
  }

  if (indeterminate || percent === null || percent === undefined || !Number.isFinite(Number(percent))) {
    dom.modelPullProgressFill.style.width = "36%";
    dom.modelPullProgressFill.classList.add("indeterminate");
    return;
  }

  const clamped = Math.max(0, Math.min(100, Number(percent)));
  dom.modelPullProgressFill.style.width = `${clamped}%`;
}

function clearPullProgress() {
  if (!dom.modelPullProgressWrap || !dom.modelPullProgressFill || !dom.modelPullProgressText) {
    return;
  }
  dom.modelPullProgressWrap.classList.add("hidden");
  dom.modelPullProgressFill.classList.remove("indeterminate", "error");
  dom.modelPullProgressFill.style.width = "0";
  dom.modelPullProgressText.textContent = "等待下载任务开始...";
}

function setInspectorTab(tab) {
  state.inspectorTab = tab;
  const isModels = tab === "models";
  const isSkills = tab === "skills";
  const isSettings = tab === "settings";

  dom.tabModelsBtn.classList.toggle("active", isModels);
  dom.tabSkillsBtn.classList.toggle("active", isSkills);
  dom.tabSettingsBtn.classList.toggle("active", isSettings);

  dom.panelModels.classList.toggle("active", isModels);
  dom.panelSkills.classList.toggle("active", isSkills);
  dom.panelSettings.classList.toggle("active", isSettings);

  dom.inspectorTitle.textContent = isModels ? "模型中心" : isSkills ? "技能中心" : "设置";
}

function openInspector(tab = state.inspectorTab) {
  state.inspectorOpen = true;
  dom.appShell.classList.add("inspector-open");
  dom.inspector.setAttribute("aria-hidden", "false");
  setInspectorTab(tab);
}

function closeInspector() {
  state.inspectorOpen = false;
  dom.appShell.classList.remove("inspector-open");
  dom.inspector.setAttribute("aria-hidden", "true");
}

function renderSettingsForm() {
  const settings = state.settings;
  dom.settingsThemeSelect.value = settings.theme || "amber";
  dom.settingsProviderSelect.value = settings.llm_provider || "ollama";
  dom.settingsLlmModelInput.value = settings.llm_model || "";
  if (!dom.settingsLlmModelInput.value) {
    dom.settingsLlmModelInput.value = (settings.llm_provider === "openai_compatible" ? settings.openai_model : settings.ollama_model) || "";
  }
  dom.settingsModelDirInput.value = settings.ollama_models_dir || "";
  dom.settingsOllamaUrlInput.value = settings.ollama_base_url || "";
  dom.settingsOpenaiBaseUrlInput.value = settings.openai_base_url || "";
  dom.settingsOpenaiModelInput.value = settings.openai_model || "";
  dom.settingsOpenaiApiKeyInput.value = "";
  dom.settingsOpenaiClearKeyInput.checked = false;
  dom.settingsOpenaiKeyStatus.textContent = settings.openai_has_api_key ? ZH.openaiKeyConfigured : ZH.openaiKeyMissing;
  dom.settingsHistoryLimitInput.value = String(settings.llm_history_limit || 20);
  dom.settingsIntentThresholdInput.value = Number(settings.intent_confidence_threshold || 0.72).toFixed(2);
  dom.settingsAutoSelectInput.checked = settings.auto_select_after_pull !== false;
  dom.settingsEnterSendInput.checked = settings.enter_to_send !== false;
  dom.settingsWebPortInput.value = String(settings.web_port_preferred || 8000);
  updateProviderDependentVisibility();
}

function updateProviderDependentVisibility() {
  const provider = dom.settingsProviderSelect.value || "ollama";
  const ollama = isOllamaProvider(provider);
  dom.settingsOllamaUrlWrap.classList.toggle("hidden", !ollama);
  dom.settingsOllamaActionsWrap.classList.toggle("hidden", !ollama);
  dom.settingsModelDirBlock.classList.toggle("hidden", !ollama);
  dom.settingsOpenaiFields.classList.toggle("hidden", ollama);
}

function renderModelFolderDetection() {
  const detection = state.modelFolderDetection || { items: [] };
  dom.settingsDetectionList.innerHTML = "";

  if (detection.note) {
    const note = document.createElement("div");
    note.className = "status-card";
    note.textContent = detection.note;
    dom.settingsDetectionList.appendChild(note);
  }

  if (!Array.isArray(detection.items) || !detection.items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = ZH.noDetection;
    dom.settingsDetectionList.appendChild(empty);
    return;
  }

  for (const item of detection.items) {
    const card = document.createElement("div");
    card.className = "entity-card";
    const isActive = detection.active_path && detection.active_path.toLowerCase() === String(item.path || "").toLowerCase();
    card.innerHTML = `
      <div class="entity-head">
        <div>
          <h4 class="entity-title">${escapeHtml(item.path || "")}</h4>
          <p class="entity-subtitle">${item.exists ? "目录存在" : "目录不存在"} · ${item.writable ? "可写" : "不可写"}</p>
        </div>
        <div class="entity-tags">
          <span class="entity-chip ${isActive ? "active" : ""}">${isActive ? `当前生效（${escapeHtml(detection.active_source || "")})` : "候选目录"}</span>
        </div>
      </div>
      <div class="entity-meta">
        <span class="entity-chip">检测到 ${Number(item.manifest_count || 0)} 个模型条目</span>
      </div>
      <div class="entity-tags">${createMetaChips((item.sample_models || []).slice(0, 6))}</div>
      <div class="entity-actions">
        <button class="secondary-btn" data-action="apply">设为模型目录</button>
      </div>
    `;
    card.querySelector("[data-action='apply']").addEventListener("click", async () => {
      dom.settingsModelDirInput.value = item.path || "";
      await saveSettings({ ollama_models_dir: item.path || "" });
    });
    dom.settingsDetectionList.appendChild(card);
  }
}

function applySettingsSnapshot(snapshot) {
  state.settings = { ...state.settings, ...(snapshot.settings || {}) };
  state.modelFolderDetection = snapshot.model_folder_detection || state.modelFolderDetection;
  setTheme(state.settings.theme);
  renderSettingsForm();
  renderModelFolderDetection();
}

function collectSettingsPayloadFromForm() {
  const historyLimit = Number.parseInt(dom.settingsHistoryLimitInput.value, 10);
  const threshold = Number.parseFloat(dom.settingsIntentThresholdInput.value);
  const preferredPort = Number.parseInt(dom.settingsWebPortInput.value, 10);
  const provider = dom.settingsProviderSelect.value || "ollama";
  const model = dom.settingsLlmModelInput.value.trim();
  const openaiApiKeyInput = dom.settingsOpenaiApiKeyInput.value.trim();
  const shouldClearOpenaiKey = !!dom.settingsOpenaiClearKeyInput.checked;

  const payload = {
    theme: dom.settingsThemeSelect.value,
    llm_provider: provider,
    llm_model: model || null,
    ollama_models_dir: dom.settingsModelDirInput.value.trim(),
    ollama_base_url: dom.settingsOllamaUrlInput.value.trim(),
    openai_base_url: dom.settingsOpenaiBaseUrlInput.value.trim(),
    openai_model: dom.settingsOpenaiModelInput.value.trim(),
    llm_history_limit: Number.isFinite(historyLimit) ? historyLimit : 20,
    intent_confidence_threshold: Number.isFinite(threshold) ? threshold : 0.72,
    auto_select_after_pull: dom.settingsAutoSelectInput.checked,
    enter_to_send: dom.settingsEnterSendInput.checked,
    web_port_preferred: Number.isFinite(preferredPort) ? preferredPort : 8000,
  };
  if (openaiApiKeyInput) {
    payload.openai_api_key = openaiApiKeyInput;
  } else if (shouldClearOpenaiKey) {
    payload.openai_api_key = "";
  }
  return payload;
}

async function loadSettings() {
  const payload = await api("/api/settings");
  applySettingsSnapshot(payload);
}

async function detectModelFolders() {
  const payload = await api("/api/settings/model-folders/detect", {
    method: "POST",
    body: JSON.stringify({}),
  });
  state.modelFolderDetection = payload.model_folder_detection || state.modelFolderDetection;
  renderModelFolderDetection();
}

async function pickModelFolder() {
  const payload = await api("/api/settings/model-folders/pick", {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (!payload.picked) {
    return false;
  }
  if (payload.path) {
    dom.settingsModelDirInput.value = payload.path;
  }
  if (payload.snapshot) {
    applySettingsSnapshot(payload.snapshot);
    await loadRuntime();
  }
  return true;
}

async function startOllamaFromUi() {
  const payload = await api("/api/ollama/start", {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (payload.runtime) {
    state.runtime = payload.runtime;
    updateModelChip();
    renderModelOptions(state.runtime.available_models || [], state.runtime.model);
    renderLocalModels();
    updateModelCenterCapabilities();
    syncModelConnectionHint();
  }
  return payload;
}

async function checkOllamaVersionFromUi() {
  return api("/api/ollama/version");
}

function formatOllamaVersionStatus(payload) {
  const lines = [];
  if (payload?.cli_available) {
    lines.push(`本机版本：${payload.cli_version || payload.cli_raw || "已安装"}`);
  } else {
    lines.push("本机版本：未检测到 Ollama 程序");
  }
  if (payload?.service_reachable) {
    lines.push(`服务状态：已连接（${payload.base_url || "N/A"}）`);
    if (payload.service_version) {
      lines.push(`服务版本：${payload.service_version}`);
    }
  } else {
    lines.push(`服务状态：未连接（${payload?.base_url || "N/A"}）`);
  }
  if (payload?.detail) {
    lines.unshift(payload.detail);
  }
  return lines.join("\n");
}

async function saveSettings(partialPayload = null) {
  const payload = partialPayload || collectSettingsPayloadFromForm();
  const snapshot = await api("/api/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  applySettingsSnapshot(snapshot);
  await loadRuntime();
  const ollamaMode = isOllamaProvider(snapshot?.settings?.llm_provider);
  setSettingsStatus(ollamaMode ? ZH.settingsSaved : ZH.settingsSavedNoRestart);
}

async function loadRuntime() {
  const payload = await api("/api/runtime");
  state.runtime = payload.runtime;
  state.settings.llm_provider = state.runtime.provider || state.settings.llm_provider;
  state.settings.llm_model = state.runtime.model || state.settings.llm_model;
  if (state.runtime.provider === "openai_compatible") {
    state.settings.openai_model = state.runtime.model || state.settings.openai_model;
  }
  if (state.runtime.provider === "ollama") {
    state.settings.ollama_model = state.runtime.model || state.settings.ollama_model;
  }
  updateModelChip();
  renderModelOptions(payload.runtime.available_models || [], payload.runtime.model);
  renderLocalModels();
  updateModelCenterCapabilities();
  renderModelTags();
  syncModelConnectionHint();
  if (state.inspectorTab === "settings") {
    renderSettingsForm();
  }
}

async function loadRemoteModels(query = state.remoteQuery) {
  state.remoteQuery = query;
  const payload = await api(`/api/model-library?q=${encodeURIComponent(query || "")}`);
  state.remoteModels = payload.items || [];
  renderRemoteModels();
}

async function loadModelTags(family) {
  if (!isOllamaProvider(state.runtime?.provider)) {
    state.activeModelFamily = "";
    state.modelTags = [];
    renderModelTags();
    return;
  }
  const targetFamily = String(family || "").trim();
  if (!targetFamily) {
    throw new Error("模型名称不能为空。");
  }
  const payload = await api(`/api/model-library/${encodeURIComponent(targetFamily)}/tags`);
  state.activeModelFamily = payload.family;
  state.modelTags = payload.items || [];
  renderModelTags();
}

async function selectDefaultModel(modelName) {
  const targetModel = String(modelName || "").trim();
  if (!targetModel) {
    throw new Error("模型名称不能为空。");
  }
  await api("/api/models/select", {
    method: "POST",
    body: JSON.stringify({ model: targetModel }),
  });
  await loadRuntime();
  if (state.activeModelFamily) {
    await loadModelTags(state.activeModelFamily);
  }
  const pendingHint = isOllamaProvider(state.runtime?.provider) && !state.runtime?.reachable ? `，${ZH.modelSetPendingOllama}` : "。";
  setPullStatus(`${ZH.modelSetDone} ${targetModel}${pendingHint}`);
}

async function loadSkills() {
  const payload = await api("/api/skills");
  state.skills = payload.items || [];
  renderSkills();
}

async function loadConversations() {
  const payload = await api("/api/conversations");
  state.conversations = payload.items;
  renderConversations();
  if (!state.activeConversationId && state.conversations.length) {
    state.activeConversationId = state.conversations[0].id;
  }
}

async function loadMessages(conversationId) {
  const payload = await api(`/api/conversations/${conversationId}/messages`);
  renderMessages(payload.items);
  dom.subtitle.textContent = payload.conversation.title;
}

async function createConversation(title = null, autoSelect = true) {
  const payload = await api("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  const conversation = payload.conversation;
  await loadConversations();
  if (autoSelect) {
    await selectConversation(conversation.id);
  }
  return conversation;
}

async function selectConversation(conversationId) {
  state.activeConversationId = conversationId;
  renderConversations();
  await loadMessages(conversationId);
  closeSidebar();
}

function autosizeComposer() {
  dom.composerInput.style.height = "auto";
  dom.composerInput.style.height = `${Math.min(dom.composerInput.scrollHeight, 230)}px`;
}

function renderUploadList() {
  if (!dom.uploadList) return;
  dom.uploadList.innerHTML = "";
  if (!state.pendingUploads.length) {
    dom.uploadList.classList.add("hidden");
    return;
  }
  dom.uploadList.classList.remove("hidden");

  const title = document.createElement("div");
  title.className = "upload-chip";
  title.textContent = `${ZH.uploadListTitle}（${state.pendingUploads.length}）`;
  dom.uploadList.appendChild(title);

  for (const item of state.pendingUploads) {
    const chip = document.createElement("div");
    chip.className = "upload-chip";
    chip.innerHTML = `
      <span class="upload-chip-name">${escapeHtml(item.name)}</span>
      <span>${formatBytes(item.size || 0)}</span>
      <button type="button" aria-label="移除附件" data-id="${escapeHtml(item.id)}">×</button>
    `;
    chip.querySelector("button").addEventListener("click", async () => {
      await removeUpload(item.id);
    });
    dom.uploadList.appendChild(chip);
  }
}

function setComposerBusy(busy) {
  dom.sendBtn.disabled = busy;
  dom.modelSelect.disabled = busy;
  if (dom.uploadFileBtn) {
    dom.uploadFileBtn.disabled = busy || state.uploadBusy;
  }
}

async function removeUpload(uploadId) {
  state.pendingUploads = state.pendingUploads.filter((item) => item.id !== uploadId);
  renderUploadList();
  try {
    await api(`/api/uploads/${encodeURIComponent(uploadId)}`, { method: "DELETE" });
  } catch {
    // Ignore delete failures for already-cleaned temporary files.
  }
}

async function handleUploadFiles(files) {
  if (!files || !files.length) {
    return;
  }
  const picked = Array.from(files);
  if (!picked.length) {
    return;
  }

  const left = Math.max(0, 5 - state.pendingUploads.length);
  if (left <= 0) {
    window.alert(ZH.uploadTooMany);
    return;
  }

  const uploadBatch = picked.slice(0, left);
  if (picked.length > left) {
    window.alert(ZH.uploadTooMany);
  }

  state.uploadBusy = true;
  if (dom.uploadFileBtn) {
    dom.uploadFileBtn.disabled = true;
    dom.uploadFileBtn.textContent = ZH.uploadPicking;
  }

  try {
    for (const file of uploadBatch) {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch("/api/uploads", {
        method: "POST",
        body: form,
      });
      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(payload.detail || ZH.uploadFailed);
      }
      if (payload.upload?.id) {
        state.pendingUploads.push(payload.upload);
      }
    }
    renderUploadList();
  } catch (error) {
    window.alert(String(error.message || error));
  } finally {
    state.uploadBusy = false;
    if (dom.uploadFileInput) {
      dom.uploadFileInput.value = "";
    }
    if (dom.uploadFileBtn) {
      dom.uploadFileBtn.disabled = state.sending;
      dom.uploadFileBtn.textContent = "📎 上传文件";
    }
  }
}

async function consumeNdjsonStream(response, onEvent) {
  if (!response.body) {
    throw new Error(ZH.streamUnsupported);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let event;
      try {
        event = JSON.parse(trimmed);
      } catch {
        continue;
      }
      await Promise.resolve(onEvent(event));
    }
  }

  const remain = buffer.trim();
  if (remain) {
    try {
      await Promise.resolve(onEvent(JSON.parse(remain)));
    } catch {
      // ignore trailing parse errors
    }
  }
}

async function pullModel(modelName, selectAfterPull = true) {
  if (state.pulling) return;
  const targetModel = String(modelName || "").trim();
  if (!targetModel) {
    setPullStatus("模型名称不能为空。", true);
    return;
  }
  if (!state.runtime?.supports_model_pull || !isOllamaProvider(state.runtime?.provider)) {
    setPullStatus(ZH.providerNoPull, true);
    setPullProgress({ text: ZH.providerNoPull, isError: true });
    return;
  }
  if (!ensureOllamaReachableForModelOps("下载模型")) {
    return;
  }
  state.pulling = true;
  clearPullProgress();
  setPullStatus(`开始处理模型：${targetModel}`);
  try {
    const response = await fetch("/api/models/pull", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: targetModel, select_after_pull: !!selectAfterPull }),
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || ZH.requestFailed);
    }

    await consumeNdjsonStream(response, async (event) => {
      if (event.type === "start") {
        const targetLine = event.target_dir ? `目标目录：${event.target_dir}` : "目标目录：使用 Ollama 当前配置";
        setPullStatus(`开始下载：${event.model}\n${targetLine}`);
        setPullProgress({
          percent: 1,
          text: `${ZH.pullStarted}：${event.model}`,
        });
        return;
      }
      if (event.type === "progress") {
        const pieces = [event.status || "下载中"];
        if (event.percent !== null && event.percent !== undefined) {
          pieces.push(`${event.percent}%`);
        }
        if (event.completed && event.total) {
          pieces.push(`${formatBytes(event.completed)} / ${formatBytes(event.total)}`);
        }
        setPullStatus(`${event.model} · ${pieces.join(" · ")}`);
        if (event.percent !== null && event.percent !== undefined) {
          setPullProgress({
            percent: Number(event.percent),
            text: `${event.status || "下载中"} · ${Number(event.percent).toFixed(1)}%`,
          });
        } else {
          setPullProgress({
            text: `${event.status || ZH.pullWaiting}`,
            indeterminate: true,
          });
        }
        return;
      }
      if (event.type === "done") {
        state.runtime = event.runtime;
        updateModelChip();
        renderModelOptions(state.runtime.available_models || [], state.runtime.model);
        renderLocalModels();
        if (state.activeModelFamily) {
          await loadModelTags(state.activeModelFamily);
        }
        await loadRemoteModels(state.remoteQuery);
        setPullStatus(`模型 ${event.model} 已就绪。${selectAfterPull ? "并已切换为默认模型。" : ""}`);
        setPullProgress({
          percent: 100,
          text: `下载完成：${event.model}`,
        });
        return;
      }
      if (event.type === "error") {
        throw new Error(event.detail || ZH.requestFailed);
      }
    });
  } catch (error) {
    setPullStatus(String(error.message || error), true);
    setPullProgress({
      text: `下载失败：${String(error.message || error)}`,
      isError: true,
    });
  } finally {
    state.pulling = false;
  }
}

async function sendMessage() {
  if (state.sending) return;
  const text = dom.composerInput.value.trim();
  if (!text && !state.pendingUploads.length) return;

  if (!state.activeConversationId) {
    const conversation = await createConversation(null, true);
    state.activeConversationId = conversation.id;
  }

  state.sending = true;
  setComposerBusy(true);
  dom.composerInput.value = "";
  autosizeComposer();
  const uploadIds = state.pendingUploads.map((item) => item.id);
  const uploadNames = state.pendingUploads.map((item) => item.name);
  const userDisplayText = text || "请阅读我上传的文件并总结重点。";
  const userBubbleText = uploadNames.length
    ? `${userDisplayText}\n\n[附件] ${uploadNames.join("，")}`
    : userDisplayText;

  const hasPlaceholder = dom.messageList.querySelector(".welcome-card, .empty-state");
  if (hasPlaceholder) {
    clearMessages();
  }
  appendMessage("user", userBubbleText);
  const typingBubble = appendTypingMessage();
  let assistantText = "";
  let requestSucceeded = false;

  try {
    const response = await fetch(`/api/conversations/${state.activeConversationId}/messages/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: userDisplayText,
        model: state.selectedModel || null,
        upload_ids: uploadIds,
      }),
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || ZH.requestFailed);
    }

    await consumeNdjsonStream(response, async (event) => {
      if (event.type === "chunk") {
        assistantText += event.content || "";
        typingBubble.innerHTML = renderMarkdownLite(assistantText || "...");
        scrollToBottom();
      } else if (event.type === "done") {
        dom.subtitle.textContent = event.conversation?.title || dom.subtitle.textContent;
        await loadConversations();
        requestSucceeded = true;
      } else if (event.type === "error") {
        throw new Error(event.detail || ZH.requestFailed);
      }
    });

    if (!assistantText.trim()) {
      typingBubble.textContent = ZH.modelEmpty;
    }
  } catch (error) {
    typingBubble.textContent = String(error.message || error);
  } finally {
    state.sending = false;
    if (requestSucceeded) {
      state.pendingUploads = [];
      renderUploadList();
    }
    setComposerBusy(false);
    dom.composerInput.focus();
    scrollToBottom();
  }
}

function openSidebar() {
  dom.sidebar.classList.add("open");
}

function closeSidebar() {
  dom.sidebar.classList.remove("open");
}

function setSidebarCollapsed(collapsed) {
  state.sidebarCollapsed = !!collapsed;
  dom.appShell.classList.toggle("sidebar-collapsed", state.sidebarCollapsed);

  if (dom.toggleHistoryBtn) {
    dom.toggleHistoryBtn.textContent = "←";
    dom.toggleHistoryBtn.setAttribute("aria-expanded", String(!state.sidebarCollapsed));
    dom.toggleHistoryBtn.title = state.sidebarCollapsed ? "展开侧边栏" : "收起侧边栏";
  }

  if (dom.expandHistoryBtn) {
    dom.expandHistoryBtn.classList.toggle("hidden", !state.sidebarCollapsed);
    dom.expandHistoryBtn.title = "展开侧边栏";
  }

  if (dom.newChatBtn) {
    dom.newChatBtn.textContent = state.sidebarCollapsed ? "+" : "+ 新建对话";
  }
}

async function submitSkillForm(event) {
  event.preventDefault();
  const payload = {
    name: dom.skillNameInput.value.trim(),
    description: dom.skillDescriptionInput.value.trim(),
    trigger_keywords: dom.skillKeywordsInput.value.trim(),
    instruction: dom.skillInstructionInput.value.trim(),
    enabled: dom.skillEnabledInput.checked,
  };
  if (!payload.name || !payload.instruction) return;

  if (state.editingSkillId) {
    await api(`/api/skills/${state.editingSkillId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  } else {
    await api("/api/skills", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  resetSkillForm();
  await loadSkills();
  await loadRuntime();
}

async function toggleSkill(skillId, enabled) {
  await api(`/api/skills/${skillId}/toggle`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
  await loadSkills();
  await loadRuntime();
}

async function handleSettingsSubmit(event) {
  event.preventDefault();
  try {
    await saveSettings();
  } catch (error) {
    setSettingsStatus(String(error.message || error), true);
  }
}

function bindEvents() {
  dom.newChatBtn.addEventListener("click", async () => {
    try {
      await createConversation(ZH.newChat, true);
    } catch (error) {
      window.alert(errorMessage(error, ZH.requestFailed));
    }
  });

  dom.sendBtn.addEventListener("click", sendMessage);

  if (dom.uploadFileBtn && dom.uploadFileInput) {
    dom.uploadFileBtn.addEventListener("click", () => {
      dom.uploadFileInput.click();
    });
    dom.uploadFileInput.addEventListener("change", async () => {
      await handleUploadFiles(dom.uploadFileInput.files);
    });
  }

  dom.modelSelect.addEventListener("change", async () => {
    const previous = state.selectedModel;
    state.selectedModel = dom.modelSelect.value;
    if (state.selectedModel) {
      try {
        await selectDefaultModel(state.selectedModel);
      } catch (error) {
        state.selectedModel = previous;
        dom.modelSelect.value = previous || "";
        setModelActionError(error, "切换模型失败");
      }
    }
  });

  dom.composerInput.addEventListener("input", autosizeComposer);
  dom.composerInput.addEventListener("keydown", (event) => {
    const enterToSend = state.settings.enter_to_send !== false;
    if (enterToSend && event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  document.querySelectorAll(".quick-action").forEach((button) => {
    button.addEventListener("click", () => {
      dom.composerInput.value = button.dataset.prompt || "";
      autosizeComposer();
      dom.composerInput.focus();
    });
  });

  dom.mobileOpenBtn.addEventListener("click", openSidebar);
  dom.mobileCloseBtn.addEventListener("click", closeSidebar);
  dom.toggleHistoryBtn.addEventListener("click", () => {
    setSidebarCollapsed(!state.sidebarCollapsed);
  });
  dom.expandHistoryBtn.addEventListener("click", () => {
    setSidebarCollapsed(false);
  });

  dom.openModelCenterBtn.addEventListener("click", async () => {
    openInspector("models");
    syncModelConnectionHint();
    if (!state.remoteModels.length) {
      try {
        await loadRemoteModels(state.remoteQuery);
      } catch (error) {
        setModelActionError(error, "加载模型库失败");
      }
    }
  });

  dom.openSkillCenterBtn.addEventListener("click", async () => {
    try {
      openInspector("skills");
      if (!state.skills.length) {
        await loadSkills();
      }
    } catch (error) {
      window.alert(errorMessage(error, ZH.requestFailed));
    }
  });

  dom.openSettingsCenterBtn.addEventListener("click", async () => {
    try {
      openInspector("settings");
      clearSettingsStatus();
      await loadSettings();
    } catch (error) {
      setSettingsStatus(errorMessage(error, ZH.requestFailed), true);
    }
  });

  dom.closeInspectorBtn.addEventListener("click", closeInspector);
  dom.tabModelsBtn.addEventListener("click", () => openInspector("models"));
  dom.tabSkillsBtn.addEventListener("click", () => openInspector("skills"));
  dom.tabSettingsBtn.addEventListener("click", () => openInspector("settings"));

  dom.modelSearchBtn.addEventListener("click", async () => {
    try {
      clearPullStatus();
      clearPullProgress();
      await loadRemoteModels(dom.modelSearchInput.value.trim());
    } catch (error) {
      setModelActionError(error, "搜索模型失败");
    }
  });

  dom.modelSearchInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      try {
        clearPullStatus();
        clearPullProgress();
        await loadRemoteModels(dom.modelSearchInput.value.trim());
      } catch (error) {
        setModelActionError(error, "搜索模型失败");
      }
    }
  });

  dom.manualModelPullBtn.addEventListener("click", async () => {
    const value = dom.manualModelInput.value.trim();
    if (!value) return;
    if (state.runtime?.supports_model_pull && isOllamaProvider(state.runtime?.provider)) {
      if (!ensureOllamaReachableForModelOps("下载模型")) {
        return;
      }
      try {
        await pullModel(value, state.settings.auto_select_after_pull !== false);
      } catch (error) {
        setModelActionError(error, "下载模型失败");
      }
      return;
    }
    try {
      await selectDefaultModel(value);
    } catch (error) {
      setModelActionError(error, "切换模型失败");
    }
  });

  dom.skillForm.addEventListener("submit", async (event) => {
    try {
      await submitSkillForm(event);
    } catch (error) {
      window.alert(errorMessage(error, ZH.requestFailed));
    }
  });
  dom.skillFormResetBtn.addEventListener("click", resetSkillForm);

  dom.settingsForm.addEventListener("submit", handleSettingsSubmit);
  dom.settingsProviderSelect.addEventListener("change", () => {
    const provider = dom.settingsProviderSelect.value || "ollama";
    updateProviderDependentVisibility();
    dom.settingsLlmModelInput.value =
      provider === "openai_compatible"
        ? dom.settingsOpenaiModelInput.value.trim() || state.settings.openai_model || "qwen-plus"
        : state.settings.ollama_model || state.runtime?.model || "";
  });
  dom.settingsOpenaiClearKeyInput.addEventListener("change", () => {
    if (dom.settingsOpenaiClearKeyInput.checked) {
      dom.settingsOpenaiApiKeyInput.value = "";
    }
  });
  dom.settingsStartOllamaBtn.addEventListener("click", async () => {
    const oldText = dom.settingsStartOllamaBtn.textContent;
    dom.settingsStartOllamaBtn.disabled = true;
    dom.settingsStartOllamaBtn.textContent = "启动中...";
    try {
      setSettingsStatus(ZH.startingOllama, false);
      const result = await startOllamaFromUi();
      if (result.reachable) {
        setSettingsStatus(result.detail || ZH.startOllamaOk, false);
      } else {
        setSettingsStatus(result.detail || ZH.startOllamaFail, true);
      }
    } catch (error) {
      setSettingsStatus(String(error.message || error), true);
    } finally {
      dom.settingsStartOllamaBtn.disabled = false;
      dom.settingsStartOllamaBtn.textContent = oldText || "启动 Ollama";
    }
  });

  if (dom.settingsOllamaVersionBtn) {
    dom.settingsOllamaVersionBtn.addEventListener("click", async () => {
      const oldText = dom.settingsOllamaVersionBtn.textContent;
      dom.settingsOllamaVersionBtn.disabled = true;
      dom.settingsOllamaVersionBtn.textContent = "检查中...";
      try {
        setSettingsStatus(ZH.checkingVersion, false);
        const payload = await checkOllamaVersionFromUi();
        const detail = formatOllamaVersionStatus(payload);
        const hasAnyVersion = Boolean(payload?.cli_available || payload?.service_reachable);
        setSettingsStatus(detail || ZH.versionUnavailable, !hasAnyVersion);
      } catch (error) {
        setSettingsStatus(errorMessage(error, ZH.requestFailed), true);
      } finally {
        dom.settingsOllamaVersionBtn.disabled = false;
        dom.settingsOllamaVersionBtn.textContent = oldText || "查看版本";
      }
    });
  }

  dom.settingsPickDirBtn.addEventListener("click", async () => {
    clearSettingsStatus();
    const oldText = dom.settingsPickDirBtn.textContent;
    dom.settingsPickDirBtn.disabled = true;
    dom.settingsPickDirBtn.textContent = "选择中...";
    try {
      setSettingsStatus(ZH.pickingDir, false);
      const picked = await pickModelFolder();
      if (!picked) {
        setSettingsStatus(ZH.pickCanceled, false);
      } else {
        setSettingsStatus(`${ZH.pickDone}${dom.settingsModelDirInput.value}`, false);
      }
    } catch (error) {
      setSettingsStatus(String(error.message || error), true);
    } finally {
      dom.settingsPickDirBtn.disabled = false;
      dom.settingsPickDirBtn.textContent = oldText || "选择文件夹";
    }
  });

  dom.settingsDetectBtn.addEventListener("click", async () => {
    clearSettingsStatus();
    try {
      setSettingsStatus(ZH.detectingModels, false);
      await detectModelFolders();
      setSettingsStatus(ZH.detectDone, false);
    } catch (error) {
      setSettingsStatus(String(error.message || error), true);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeInspector();
      closeSidebar();
    }
  });

  document.addEventListener("mousedown", (event) => {
    if (!state.inspectorOpen) return;
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (dom.inspector.contains(target)) return;
    if (
      dom.openModelCenterBtn.contains(target) ||
      dom.openSkillCenterBtn.contains(target) ||
      dom.openSettingsCenterBtn.contains(target)
    ) {
      return;
    }
    closeInspector();
  });
}

async function boot() {
  bindEvents();
  setSidebarCollapsed(false);
  autosizeComposer();
  renderUploadList();
  setComposerBusy(false);
  clearPullProgress();
  await loadSettings();
  await loadRuntime();
  await loadSkills();
  try {
    await loadRemoteModels("");
  } catch (error) {
    setPullStatus(`模型库暂时不可用：${error.message || error}`, true);
  }
  await loadConversations();
  if (!state.conversations.length) {
    await createConversation(ZH.newChat, true);
  } else if (state.activeConversationId) {
    await loadMessages(state.activeConversationId);
  }
}

window.addEventListener("unhandledrejection", (event) => {
  const detail = errorMessage(event.reason, ZH.requestFailed);
  setPullStatus(`${ZH.actionFailed}：${detail}`, true);
});

window.addEventListener("error", (event) => {
  const detail = errorMessage(event.error || event.message, ZH.requestFailed);
  if (!detail) return;
  setPullStatus(`${ZH.actionFailed}：${detail}`, true);
});

boot().catch((error) => {
  clearMessages();
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = `${ZH.initFailed}${error.message || error}`;
  dom.messageList.appendChild(empty);
});
