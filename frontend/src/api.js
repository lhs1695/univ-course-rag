function errorMessage(status, body) {
  const detail = body?.detail;
  if (typeof detail === "string" && detail) {
    return detail;
  }
  if (Array.isArray(detail) && detail[0]?.msg) {
    return detail[0].msg;
  }
  if (status === 401) {
    return "未登录或会话已失效";
  }
  if (status === 403) {
    return "没有这门课的访问权限";
  }
  return `请求失败（${status}）`;
}

export async function api(path, options = {}) {
  const { json, formData, ...rest } = options;
  const headers = { Accept: "application/json", ...(rest.headers || {}) };
  let body = rest.body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (formData !== undefined) {
    body = formData;
  }
  const response = await fetch(path, {
    credentials: "include",
    ...rest,
    headers,
    body,
  });
  if (response.status === 204) {
    return null;
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorMessage(response.status, payload));
    error.status = response.status;
    throw error;
  }
  return payload;
}
