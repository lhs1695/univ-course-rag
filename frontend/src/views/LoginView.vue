<template>
  <div class="entry-layout">
    <section class="entry-story">
      <div class="entry-heading"><span class="tiny-bookmark" aria-hidden="true"></span><span>你的课内阅读伙伴</span></div>
      <h1>好问题，<br>值得翻到原文。</h1>
      <p class="entry-description">把课堂上的疑问带来。<br>在课程资料里寻找答案，也找到答案的出处。</p>
      <div class="reading-illustration" aria-hidden="true"><div class="illustration-page left-page"><span class="page-title">关于知识的笔记</span><i></i><i></i><i class="highlight-line"></i><i></i><i></i><span class="page-foot">阅读，思考。</span></div><div class="illustration-page right-page"><span class="paper-bookmark"></span><span class="quote-symbol">“</span><span class="paper-quote">有依据，<br>才有进一步<br>思考的起点。</span><i></i><i></i><span class="page-foot">回到原文核对</span></div><span class="illustration-caption">提问 / 阅读 / 核对</span></div>
    </section>
    <section class="entry-form" aria-labelledby="login-heading">
      <span class="welcome-mark" aria-hidden="true">课</span><h2 id="login-heading">回到你的课程</h2><p>登录后，继续探索课堂里的问题。</p>
      <el-form :model="form" label-position="top" :aria-describedby="loginError ? 'login-error' : undefined" @submit.prevent="onSubmit">
        <el-form-item label="用户名"><el-input id="username" v-model="form.username" autocomplete="username" placeholder="输入你的用户名" @input="loginError = ''" :disabled="loading" /></el-form-item>
        <el-form-item label="密码"><el-input id="password" v-model="form.password" type="password" show-password autocomplete="current-password" placeholder="输入密码" @input="loginError = ''" :disabled="loading" /></el-form-item>
        <p v-if="loginError" id="login-error" class="entry-error" role="alert">{{ loginError }}</p>
        <el-button class="entry-submit" type="primary" native-type="submit" :disabled="!form.username.trim() || !form.password" :loading="loading">登录课程知识库</el-button>
      </el-form>
      <p class="entry-help">使用学校分配的账号。还没有账号或课程？<br>请联系本课教师或管理员。</p>
    </section>
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
