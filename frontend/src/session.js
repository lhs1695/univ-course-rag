import { reactive } from "vue";
import { api } from "./api";

export const session = reactive({
  user: null,
  ready: false,
});

export async function refreshMe() {
  try {
    session.user = await api("/auth/me");
  } catch {
    session.user = null;
  } finally {
    session.ready = true;
  }
}

export async function login(username, password) {
  session.user = await api("/auth/login", {
    method: "POST",
    json: { username, password },
  });
}

export async function logout() {
  await api("/auth/logout", { method: "POST" });
  session.user = null;
}
