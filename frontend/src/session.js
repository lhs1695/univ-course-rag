import { reactive } from "vue";
import { api } from "./api.js";
import { clearCourseAccess } from "./courseAccess.js";
import { clearDrafts } from "./drafts.js";

export const session = reactive({
  user: null,
  ready: false,
  error: null,
  retryPath: "",
});
let authVersion = 0;

window.addEventListener("access-denied", ({ detail }) => {
  if (detail.status === 401) {
    authVersion += 1;
    session.user = null;
    session.ready = true;
    session.error = { status: 401, message: "会话已失效，请重新登录；问句草稿仅在本页内存保留。" };
    clearCourseAccess();
  } else if (detail.status === 403 && detail.path.startsWith("/admin/")) {
    refreshMe();
  }
});

export async function refreshMe() {
  const version = ++authVersion;
  try {
    const user = await api("/auth/me");
    if (version !== authVersion) return;
    if (session.user?.id !== user.id || session.user?.role !== user.role) clearCourseAccess();
    session.user = user;
    session.error = null;
    return true;
  } catch (error) {
    if (version !== authVersion) return false;
    session.error = error;
    // A transport failure does not prove that the authenticated session expired.
    if (error.status === 401) {
      session.user = null;
      clearCourseAccess();
    }
    return false;
  } finally {
    if (version === authVersion) session.ready = true;
  }
}

export async function login(username, password) {
  const version = ++authVersion;
  const user = await api("/auth/login", {
    method: "POST",
    json: { username, password },
  });
  if (version === authVersion) {
    session.user = user;
    session.ready = true;
  }
  session.error = null;
}

export async function logout() {
  const version = ++authVersion;
  await api("/auth/logout", { method: "POST" });
  if (version !== authVersion) return;
  session.user = null;
  session.ready = true;
  session.error = null;
  clearDrafts();
  clearCourseAccess();
}
