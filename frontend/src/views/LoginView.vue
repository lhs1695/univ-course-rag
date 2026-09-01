<template>
  <div class="login-page">
    <el-card class="login-card" shadow="never">
      <template #header>登录</template>
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
      <p class="hint">演示账号用户名见仓库 AGENTS.md；密码只在本机 .env。</p>
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
  loading.value = true;
  try {
    await login(form.username.trim(), form.password);
    const next = typeof route.query.next === "string" ? route.query.next : "";
    if (next.startsWith("/")) {
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
  color: #909399;
  font-size: 12px;
}
</style>
