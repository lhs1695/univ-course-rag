<template>
  <div class="page">
    <h2>用户</h2>
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
        <el-button type="primary" native-type="submit" :loading="creating">创建</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="users" v-loading="loading">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="role" label="角色" width="120" />
    </el-table>
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
