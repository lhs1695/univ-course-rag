<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">管理后台</p><h1>账号管理</h1><p class="page-description">创建教师、学生与管理员账号。账号身份与课程内授权分别管理。</p></header>
    <section class="panel-card">
    <h2>创建账号</h2>
    <el-form :inline="true" :model="form" @submit.prevent="onCreate">
      <el-form-item label="用户名">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password />
      </el-form-item>
      <el-form-item label="角色">
        <el-select v-model="form.role" style="width: 120px">
          <el-option label="学生" value="student" />
          <el-option label="教师" value="teacher" />
          <el-option label="管理员" value="admin" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="creating">创建账号</el-button>
      </el-form-item>
    </el-form>
    </section>
    <section class="panel-card">
    <h2>已有账号</h2>
    <el-table :data="users" v-loading="loading" empty-text="还没有账号，可在上方创建教师或学生账号">
      <el-table-column prop="username" label="用户名" />
      <el-table-column label="全局身份" width="120"><template #default="{ row }">{{ { student: '学生', teacher: '教师', admin: '管理员' }[row.role] || row.role }}</template></el-table-column>
    </el-table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const users = ref([]);
const loading = ref(true);
const creating = ref(false);
const form = reactive({ username: "", password: "", role: "student" });

async function loadUsers() {
  users.value = await api("/admin/users");
}

onMounted(async () => {
  try {
    await loadUsers();
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
});

async function onCreate() {
  if (creating.value) return;
  const username = form.username.trim();
  if (!username || !form.password) {
    ElMessage.warning("请填写用户名和密码");
    return;
  }
  creating.value = true;
  try {
    await api("/admin/users", {
      method: "POST",
      json: { username, password: form.password, role: form.role },
    });
    form.username = "";
    form.password = "";
    ElMessage.success("已创建");
    await loadUsers();
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    creating.value = false;
  }
}
</script>
