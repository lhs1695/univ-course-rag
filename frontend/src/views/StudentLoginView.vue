<template>
  <div class="student-ui study-login">
    <section class="login-story"><div class="login-story-brand"><StudyIcon name="book"/>课程知识库</div><div class="login-story-copy"><h1>从一个问题，<br>走向真正理解。</h1><p>你的课程，你的资料。<br>每一次追问，都有原文可循。</p><div class="login-paper"><span class="paper-tab">学习手记</span><div class="login-paper-title"><StudyIcon name="chat"/> 提出一个好问题</div><div class="paper-rule"></div><p>在课内资料中寻找答案</p><div class="paper-lines"><i></i><i></i><i></i></div><div class="paper-reference"><StudyIcon name="file"/><span>回答依据</span><b>回到原文页 <StudyIcon name="external"/></b></div></div></div><div class="login-story-footer">有依据，可核对。</div><span class="story-dot dot-one"></span><span class="story-dot dot-two"></span></section>
    <main id="main-content" tabindex="-1" class="login-form-region"><router-link class="login-mobile-brand" to="/login"><StudyIcon name="book"/>课程知识库</router-link><div class="login-form-wrap"><span class="login-bookmark"><StudyIcon name="book"/></span><h2>回到你的学习空间</h2><p class="login-lead">登录后，选择课程，开始你的下一次追问。</p><form @submit.prevent="onSubmit" :aria-describedby="loginError ? 'login-error' : undefined"><label for="login-username">用户名</label><el-input id="login-username" v-model="form.username" @input="loginError = ''" autocomplete="username" placeholder="输入你的用户名" required/><label for="login-password">密码</label><el-input id="login-password" v-model="form.password" @input="loginError = ''" type="password" show-password autocomplete="current-password" placeholder="输入密码" required/><p v-if="loginError" id="login-error" class="login-error" role="alert">{{ loginError }}</p><el-button class="login-submit" type="primary" native-type="submit" :loading="loading">进入课程知识库 <StudyIcon v-if="!loading" name="arrow"/></el-button></form><div class="login-help"><strong>第一次使用？</strong><p>请使用管理员分配的账号。<br>如需加入课程或重置密码，请联系本课教师或管理员。</p></div></div><footer>课程内的智能问答 · 为每个答案保留来路</footer></main>
  </div>
</template>
<script setup>
import StudyIcon from "../components/StudyIcon.vue";
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
