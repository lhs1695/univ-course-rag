<template>
  <div class="login-page">
    <el-card class="login-card" shadow="never">
      <template #header><h1 class="login-title">课程知识库</h1><p class="login-subtitle">登录后，回到你的课程与资料。</p></template>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <p class="hint">使用管理员分配的账号登录。需要加入课程时，请联系本课教师或管理员。</p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { login, session } from "../session";

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const form = reactive({ username: "", password: "" });

async function onSubmit() {
  if (loading.value) return;
  loading.value = true;
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
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.hint {
  margin: 0;
  color: #6a7872;
  font-size: 12px;
  line-height: 1.75;
}
.login-title { color: #1f3b34; font-size: 27px; line-height: 1.3; margin: 0; }
.login-subtitle { font-size: 13px; font-weight: 400; color: #65736e; margin: 7px 0 0; }
</style>
