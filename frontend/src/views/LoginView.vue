<template>
  <div class="entry-layout">
    <section class="entry-guide" aria-labelledby="entry-title">
      <p class="eyebrow">课程学习空间</p><h1 id="entry-title">课内资料，<br>有据可查。</h1>
      <p class="entry-description">登录后，进入已授权的课程。<br>阅读资料，提出问题，回到原文核对。</p>
      <ol class="entry-steps"><li><span>01</span><div><strong>选择课程</strong><p>在自己的课程书架中开始。</p></div></li><li><span>02</span><div><strong>带着问题阅读</strong><p>回答以本课可检索资料为依据。</p></div></li><li><span>03</span><div><strong>打开原文核对</strong><p>从引用回到资料，有页码时定位对应页。</p></div></li></ol>
      <p class="entry-boundary">仅在课程授权范围内访问资料与问答。</p>
    </section>
    <section class="entry-form" aria-labelledby="login-heading">
      <p class="eyebrow">账号登录</p><h2 id="login-heading">回到你的课程</h2><p>使用学校分配的账号登录。</p>
      <el-form :model="form" label-position="top" :aria-describedby="loginError ? 'login-error' : undefined" @submit.prevent="onSubmit">
        <el-form-item label="用户名" for="username"><el-input id="username" v-model="form.username" autocomplete="username" placeholder="输入你的用户名" @input="loginError = ''" :disabled="loading" /></el-form-item>
        <el-form-item label="密码" for="password"><el-input id="password" v-model="form.password" type="password" show-password autocomplete="current-password" placeholder="输入密码" @input="loginError = ''" :disabled="loading" /></el-form-item>
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
