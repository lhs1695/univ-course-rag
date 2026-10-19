<template>
  <div class="study-login study-app">
    <section class="study-login-story"><div class="study-brand"><StudyIcon /><span>课程知识库<small>有依据，可核对</small></span></div><div class="study-login-message"><span class="study-kicker">属于你的课程学习空间</span><h1>好问题，<br>值得有出处的回答。</h1><p>从课内资料出发，把每一次疑问，<br>变成有据可循的理解。</p><div class="study-paper"><div class="study-paper-title"><StudyIcon name="book" /><span>一条完整的学习路径</span></div><ol><li><b>01</b><span>提出问题<small>聚焦正在学习的课程</small></span></li><li><b>02</b><span>阅读回答<small>理解内容，也看见依据</small></span></li><li><b>03</b><span>核对原文<small>沿着引用，回到资料的那一页</small></span></li></ol><span class="study-paper-page">每一步，都离理解更近一点。</span></div></div><p class="study-login-bottom">课程内的知识，有迹可循。</p></section>
    <section class="study-login-form"><div class="study-login-form-inner"><p class="study-kicker">欢迎回来</p><h2>登录你的学习空间</h2><p class="study-muted">使用已分配的账号，继续课程学习。</p><form @submit.prevent="submit"><label for="study-username">用户名</label><input id="study-username" v-model="form.username" autocomplete="username" required placeholder="请输入用户名" :aria-invalid="Boolean(error)" @input="error = ''" /><div class="study-password-label"><label for="study-password">密码</label><button type="button" :aria-pressed="showPassword" @click="showPassword = !showPassword">{{ showPassword ? '隐藏密码' : '显示密码' }}</button></div><input id="study-password" v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" required placeholder="请输入密码" :aria-describedby="error ? 'study-login-error' : undefined" :aria-invalid="Boolean(error)" @input="error = ''" /><p v-if="error" id="study-login-error" class="study-error" role="alert">{{ error }}</p><button class="study-button study-primary" type="submit" :disabled="loading">{{ loading ? '正在登录…' : '进入课程知识库' }}<StudyIcon name="arrow" /></button></form><div class="study-login-help"><strong>还没有账号或课程？</strong><p>请联系本课教师或管理员分配账号与课程。登录后仅显示你已加入的课程。</p></div></div><span class="study-login-privacy">课内资料 · 专注学习 · 核对原文</span></section>
  </div>
</template>
<script setup>
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { login, session } from '../session';
import StudyIcon from '../components/StudyIcon.vue';
import '../student.css';
const route = useRoute(), router = useRouter();
const form = reactive({ username: '', password: '' }), loading = ref(false), error = ref(''), showPassword = ref(false);
async function submit() { if (loading.value) return; loading.value = true; error.value = ''; try { await login(form.username.trim(), form.password); const next = typeof route.query.next === 'string' ? route.query.next : ''; await router.replace(next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login') ? next : session.user?.role === 'admin' ? '/admin/users' : '/courses'); } catch (e) { error.value = e.message; } finally { loading.value = false; } }
</script>
