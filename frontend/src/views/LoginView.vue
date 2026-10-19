<template>
  <div class="entry-layout">
    <section class="entry-story" aria-labelledby="entry-title">
      <router-link to="/login" class="study-brand"><span class="study-seal">课</span>课程知识库</router-link>
      <div class="entry-statement"><h1 id="entry-title">把疑问展开，<br>让理解有据。</h1><p>从课堂上的一个疑问出发，<br>在课程资料中，找到可以核对的答案。</p></div>
      <div class="entry-index"><span>提出问题</span><span>阅读回答</span><span>回到原页</span></div>
      <div class="entry-foot">每一次理解，都有来处。</div>
    </section>
    <section class="entry-form-panel" aria-labelledby="login-title">
      <div class="entry-form-wrap"><h2 id="login-title">回到你的课程</h2><p class="entry-intro">使用分配给你的账号，继续学习。</p>
      <el-form :model="form" label-position="top" :aria-describedby="loginError ? 'login-error' : undefined" @submit.prevent="onSubmit">
        <el-form-item label="用户名" prop="username"><el-input v-model="form.username" aria-label="用户名" placeholder="请输入用户名" @input="loginError = ''" autocomplete="username" required /></el-form-item>
        <el-form-item label="密码" prop="password"><el-input v-model="form.password" aria-label="密码" placeholder="请输入密码" @input="loginError = ''" type="password" show-password autocomplete="current-password" required /></el-form-item>
        <p v-if="loginError" id="login-error" class="login-error" role="alert">{{ loginError }}</p>
        <el-button class="entry-submit" type="primary" native-type="submit" :loading="loading">进入课程知识库 <StudyArrow /></el-button>
      </el-form>
      <p class="entry-help">还没有账号或课程？<br>请联系本课教师或管理员获取访问权限。</p></div>
      <p class="entry-bottom">课内资料 · 有据问答 · 原页核对</p>
    </section>
  </div>
</template>
<script setup>
import StudyArrow from "../components/StudyArrow.vue";
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
