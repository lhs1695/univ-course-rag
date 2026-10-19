<template>
  <div class="study-entry">
    <header class="entry-brand"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M4 5h8l2 3 2-3h8v17h-8l-2 2-2-2H4zM14 8v16M7 9h4M17 9h4" /></svg><span>课程知识库</span></header>
    <main class="entry-layout">
      <section class="entry-argument" aria-label="学习方式"><div class="entry-copy"><h2>好问题，<br>值得翻到原文。</h2><p>在你的课程里提问，<br>让理解建立在可以核对的依据上。</p></div><div class="entry-reading"><div><span>从疑问出发</span><span aria-hidden="true">→</span><span>带着依据理解</span></div><p>回答附上资料引用与页码。<br>点开引用，继续读原来的那一页。</p></div><footer>提问有范围，回答有出处。</footer></section>
      <section class="entry-form-panel"><div class="entry-form-heading"><h1>登录课程知识库</h1><p>回到你的课程，继续探索。</p></div><form @submit.prevent="onSubmit" :aria-describedby="loginError ? 'login-error' : undefined"><label for="login-username">用户名</label><el-input id="login-username" v-model="form.username" required autocomplete="username" placeholder="输入分配给你的账号" @input="loginError = ''" /><label for="login-password">密码</label><el-input id="login-password" v-model="form.password" required type="password" show-password autocomplete="current-password" placeholder="输入密码" @input="loginError = ''" /><p v-if="loginError" id="login-error" class="study-error" role="alert">{{ loginError }}</p><button class="ink-button entry-submit" :disabled="loading || !form.username.trim() || !form.password" type="submit">{{ loading ? '正在登录…' : '登录' }}<span aria-hidden="true">→</span></button></form><p class="entry-help">使用教师或管理员分配的账号。<br>需要账号或课程权限？请联系任课教师。</p></section>
    </main>
    <footer class="entry-footer">课程内的智能问答 · 有依据，可核对</footer>
  </div>
</template>
<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login, session } from "../session";

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const loginError = ref("");
const form = reactive({ username: "", password: "" });

async function onSubmit() {
  if (loading.value) return;
  loading.value = true;
  loginError.value = "";
  try {
    await login(form.username.trim(), form.password);
    const next = typeof route.query.next === "string" ? route.query.next : "";
    if (next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login")) {
      await router.replace(next);
    } else if (session.user?.role === "admin") {
      await router.replace("/admin/users");
    } else {
      await router.replace("/courses");
    }
  } catch (error) {
    loginError.value = error.status === 401 ? "用户名或密码不正确，请重新输入。" : error.message;
  } finally {
    loading.value = false;
  }
}
</script>
