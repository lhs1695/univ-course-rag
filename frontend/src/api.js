const inFlightWrites = new Set();

export class ApiError extends Error {
  constructor(message, status = 0, code = "REQUEST_FAILED") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const serviceMessages = {
  MODEL_NOT_CONFIGURED: "AI 服务配置不可用，请联系管理员核对配置。",
  DATABASE_UNAVAILABLE: "数据库暂时不可用，请稍后重试。",
  UPSTREAM_UNAVAILABLE: "上游 AI 服务暂时不可用，请稍后重试。",
  UPSTREAM_TIMEOUT: "上游 AI 服务响应超时，请稍后显式重试。",
  QUESTION_GROUPING_DISABLED: "问题语义分组尚未启用。基础统计仍可查看；这次没有把问句发到嵌入服务。",
  QUESTION_GROUPING_FAILED: "候选分组没有完成，没有可展示的分组结果。请稍后重试。",
  QUESTION_GROUPING_LIMIT: "本次窗口内的问句数量或文本超出分组上限，请缩小时间范围后重试。",
};
const knownDetails = {
  external_processing_confirmation_required: "请先勾选本次外发处理确认，再创建或恢复调查。",
  active_investigation_conflict: "本课已有活跃调查，请先完成或取消该任务。",
  idempotency_conflict: "创建请求已变化，请发起新的调查。",
  investigation_checkpoint_unsafe: "检查点无法安全恢复，请核对来源后显式重试。",
  source_unavailable: "调查依据已不可用，请核对课程资料与授权。",
  agent_budget_exhausted: "累计预算已耗尽，不能继续此任务。",

  "Invalid credentials": "用户名或密码不正确，请重新输入。",
  "User not found": "找不到该学生账号，请先让管理员创建。",
  "Already a member": "该账号已加入课程，请刷新成员列表。",
  "Username taken": "用户名已存在，请换一个用户名。",
  "Can only add students": "这里只能加入已有学生账号。",
  "Can only remove students": "这里只能移出课内学生。",
  "Ingest job is active or already succeeded": "入库任务仍在运行或已完成，请刷新资料状态。",
  "Ingest job is missing": "入库任务不存在，请联系管理员核对。",
  "Upload storage unavailable": "上传存储不可用，请联系管理员检查磁盘和目录权限。",
  "Document storage cleanup unavailable": "原文件清理失败，资料记录仍保留；请稍后重试删除。",
  "empty file": "文件为空，请选择有内容的文件。",
  "Time window must overlap retained history": "所选时间与当前可统计的留存窗口没有交集，或开始时刻不早于结束时刻。",
  "Explicit external processing confirmation required": "需要先确认本次会把问句原文发送到已配置的嵌入服务。",
};
function responseError(status, body) {
  const code = body?.error_code;
  if (serviceMessages[code]) return new ApiError(serviceMessages[code], status, code);
  if (knownDetails[body?.detail]) return new ApiError(knownDetails[body.detail], status);
  const message = status === 401 ? "未登录或会话已失效，请重新登录。"
    : status === 403 ? "没有此操作的权限，请返回课程列表核对授权。"
    : status === 404 ? "课程、资料或目标对象已不存在，请刷新列表。"
    : status === 409 ? "当前状态冲突，请刷新后核对，勿重复提交。"
    : status === 413 ? "文件过大，请缩小后重试。"
    : status === 422 ? "输入格式不正确，请检查必填项。"
    : status === 400 ? "请求或文件格式不支持，请检查输入及文件类型。"
    : status === 504 ? "服务响应超时，请稍后显式重试。"
    : "服务暂时不可用，请稍后重试。";
  return new ApiError(message, status, `HTTP_${status}`);
}

export async function api(path, options = {}) {
  const { json, formData, timeoutMs = 90000, signal, onEvent, ...rest } = options;
  const method = (rest.method || "GET").toUpperCase();
  const writeKey = ["GET", "HEAD"].includes(method) ? null : `${method}:${path}`;
  if (writeKey && inFlightWrites.has(writeKey)) {
    throw new ApiError("操作正在进行，请等待结果。", 409, "REQUEST_IN_PROGRESS");
  }
  if (writeKey) inFlightWrites.add(writeKey);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = { Accept: onEvent ? "text/event-stream" : "application/json", ...(rest.headers || {}) };
    let body = rest.body;
    if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(json);
    } else if (formData !== undefined) body = formData;
    const response = await fetch(path, {
      credentials: "include", ...rest, headers, body,
      signal: signal ? AbortSignal.any([signal, controller.signal]) : controller.signal,
    });
    if (response.status === 204) return null;
    if (response.ok && onEvent) return await readAskStream(response, onEvent);
    let payload;
    try { payload = await response.json(); }
    catch (error) {
      if (controller.signal.aborted || signal?.aborted) throw error;
      payload = null;
    }
    if (!response.ok) {
      const courseId = path.match(/^\/courses\/([^/?]+)/)?.[1];
      const missingCourse = response.status === 404 && /^\/courses\/[^/?]+$/.test(path);
      if ((response.status === 401 && path !== "/auth/login") || response.status === 403 || missingCourse) {
        window.dispatchEvent(new CustomEvent("access-denied", {
          detail: { status: response.status, path, courseId },
        }));
      }
      throw responseError(response.status, payload);
    }
    if (payload === null) throw new ApiError("服务返回格式异常，请稍后重试。", response.status, "INVALID_RESPONSE");
    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) {
      throw new ApiError("请求等待超时，服务器可能仍在处理；请先核对结果再重试。", 0, "REQUEST_TIMEOUT");
    }
    if (signal?.aborted) throw new ApiError("请求已中断，输入已保留。", 0, "REQUEST_CANCELLED");
    throw new ApiError("网络连接失败，请检查连接后显式重试。", 0, "NETWORK_ERROR");
  } finally {
    clearTimeout(timer);
    if (writeKey) inFlightWrites.delete(writeKey);
  }
}

async function readAskStream(response, onEvent) {
  if (!response.body || !response.headers.get("content-type")?.includes("text/event-stream")) {
    throw new ApiError("服务返回格式异常，请稍后重试。", response.status, "INVALID_RESPONSE");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      // Normalize after decoding so UTF-8 and SSE frame boundaries may span reads.
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        const lines = frame.split(/\r?\n/);
        const event = lines.find(line => line.startsWith("event:"))?.slice(6).trim();
        const data = lines.filter(line => line.startsWith("data:"))
          .map(line => line.slice(5).trimStart()).join("\n");
        if (!data) continue;
        let payload;
        try { payload = JSON.parse(data); }
        catch { throw new ApiError("回答流格式异常，请重试。", 0, "INVALID_RESPONSE"); }
        if (event === "error") throw responseError(503, payload);
        if (event === "final") return payload;
        if (event === "phase" || event === "delta") onEvent(event, payload);
      }
      if (done) throw new ApiError("回答连接已中断，请重试本次问题。", 0, "STREAM_INCOMPLETE");
    }
  } finally {
    try { await reader.cancel(); } catch { /* Already aborted or closed. */ }
    reader.releaseLock();
  }
}

export function askStream(path, options) {
  return api(`${path}/stream`, options);
}

const investigationPath = (courseId, taskId = "") => `/courses/${courseId}/agent-tasks${taskId ? `/${taskId}` : ""}`;
export const investigationApi = {
  create(courseId, body) {
    if (!body.confirm_external_processing) {
      return Promise.reject(new ApiError(knownDetails.external_processing_confirmation_required, 422));
    }
    return api(investigationPath(courseId), { method: "POST", json: body });
  },
  async read(courseId, taskId) {
    const task = await api(investigationPath(courseId, taskId));
    const events = await api(`${investigationPath(courseId, taskId)}/events`);
    return { ...task, events };
  },
  report: (courseId, taskId) => api(`${investigationPath(courseId, taskId)}/report`),
  action(courseId, taskId, action, confirmed, mode = "fake") {
    if (["resume", "retry"].includes(action) && !confirmed) {
      return Promise.reject(new ApiError(knownDetails.external_processing_confirmation_required, 422));
    }
    return api(`${investigationPath(courseId, taskId)}/${action}`, {
      method: "POST", json: { confirm_external_processing: confirmed, mode }, timeoutMs: 130000,
    });
  },
};
