<template>
  <div class="page">
    <header class="page-heading"><h1>账号管理</h1></header>
    <section class="panel-card">
    <h2>创建账号</h2>
    <el-form :inline="true" :model="form" :disabled="creating" @submit.prevent="onCreate">
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
        <el-button :disabled="creating" @click="clearForm">清空</el-button>
      </el-form-item>
    </el-form>
    </section>
    <section class="panel-card">
    <h2>已有账号</h2>
    <p class="account-note">演示账号：admin / teacher / student；默认密码分别为 change-me-admin、change-me-teacher、change-me-student。</p>
    <el-input v-model="userFilter" clearable placeholder="按用户名筛选" style="max-width: 280px; margin-bottom: 12px" aria-label="按用户名筛选账号" />
    <el-table :data="filteredUsers" v-loading="loading" empty-text="还没有账号，可在上方创建教师或学生账号">
      <el-table-column prop="username" label="用户名" />
      <el-table-column label="系统角色" width="120"><template #default="{ row }">{{ { student: '学生', teacher: '教师', admin: '管理员' }[row.role] || row.role }}</template></el-table-column>
    </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

// Known API contract: GET/POST only; do not probe unsupported write endpoints.
const roleNames = { student: "学生", teacher: "教师", admin: "管理员" };
function clearForm() { Object.assign(form, { username: "", password: "", role: "student" }); }
const users = ref([]);
const userFilter = ref("");
const filteredUsers = computed(() => {
  const q = userFilter.value.trim().toLowerCase();
  if (!q) return users.value;
  return users.value.filter((row) => String(row.username || "").toLowerCase().includes(q));
});
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
    if (error.status !== 401) ElMessage.error(error.message);
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
  const payload = { username, password: form.password, role: form.role };
  try {
    try {
      await ElMessageBox.confirm(`为「${username}」创建系统角色为「${roleNames[payload.role]}」的账号？课程授权需另行设置。`, "确认账号角色", { confirmButtonText: "确认创建", cancelButtonText: "取消", type: "warning" });
    } catch { return; }
    await api("/admin/users", {
      method: "POST",
      json: payload,
    });
    clearForm();
    ElMessage.success("已创建");
    await loadUsers();
  } catch (error) {
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    creating.value = false;
  }
}
</script>
