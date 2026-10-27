<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">管理 / 账号</p><h1>账号管理</h1><p class="page-description">创建与查找账号；课程访问由课内授权决定。</p></header>
    <section class="panel-card">
    <h2>创建账号</h2>
    <el-form :inline="true" :model="form" :disabled="creating" @submit.prevent="onCreate">
      <el-form-item label="用户名">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password />
      </el-form-item>
      <el-form-item label="姓名"><el-input v-model="form.full_name" maxlength="100" /></el-form-item>
      <el-form-item label="学院"><el-select v-model="form.college_id" aria-label="新账号学院" clearable style="width:200px"><el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
      <el-form-item v-if="form.role === 'student'" label="学号"><el-input v-model="form.student_number" maxlength="64" placeholder="学生名单匹配用" /></el-form-item>
      <el-form-item v-else label="工号"><el-input v-model="form.employee_number" maxlength="64" placeholder="选填" /></el-form-item>
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
      <el-table-column prop="full_name" label="姓名" />
      <el-table-column prop="student_number" label="学号" />
      <el-table-column prop="employee_number" label="工号" />
      <el-table-column prop="college_name" label="学院" />
      <el-table-column label="系统角色" width="120"><template #default="{ row }">{{ { student: '学生', teacher: '教师', admin: '管理员' }[row.role] || row.role }}</template></el-table-column>
      <el-table-column label="资料"><template #default="{row}"><el-button link @click="editing = {...row}">编辑资料</el-button></template></el-table-column>
    </el-table>
    </section>
    <el-dialog :model-value="Boolean(editing)" title="维护个人资料" @close="editing = null">
      <el-form v-if="editing" :disabled="saving" @submit.prevent="saveProfile">
        <el-form-item label="姓名"><el-input v-model="editing.full_name" maxlength="100" /></el-form-item>
        <el-form-item label="学院"><el-select v-model="editing.college_id" aria-label="账号所属学院" clearable style="width:240px"><el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item v-if="editing.role === 'student'" label="学号"><el-input v-model="editing.student_number" maxlength="64" /></el-form-item>
        <el-form-item v-else label="工号"><el-input v-model="editing.employee_number" maxlength="64" /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="saving">保存资料</el-button>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

const roleNames = { student: "学生", teacher: "教师", admin: "管理员" };
function clearForm() { Object.assign(form, { username: "", password: "", role: "student", full_name: "", student_number: "", employee_number: "", college_id: "" }); }
function numberFields(profile) {
  const field = profile.role === "student" ? "student_number" : "employee_number";
  return { [field]: profile[field]?.trim() || null };
}
const editing = ref(null), saving = ref(false);
async function saveProfile() {
  if (saving.value || !editing.value) return;
  saving.value = true;
  try {
    await api(`/admin/users/${editing.value.id}`, { method: "PATCH", json: { full_name: editing.value.full_name?.trim() || null, college_id: editing.value.college_id || null, ...numberFields(editing.value) } });
    editing.value = null; await loadUsers(); ElMessage.success("资料已保存");
  } catch (error) { ElMessage.error(error.message); } finally { saving.value = false; }
}
const users = ref([]);
const colleges = ref([]);
const userFilter = ref("");
const filteredUsers = computed(() => {
  const q = userFilter.value.trim().toLowerCase();
  if (!q) return users.value;
  return users.value.filter((row) => String(row.username || "").toLowerCase().includes(q));
});
const loading = ref(true);
const creating = ref(false);
const form = reactive({ username: "", password: "", role: "student", full_name: "", student_number: "", employee_number: "", college_id: "" });

async function loadUsers() {
  users.value = await api("/admin/users");
}

onMounted(async () => {
  try {
    await Promise.all([loadUsers(), api("/admin/colleges").then(rows => { colleges.value = rows; })]);
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
  const payload = { username, password: form.password, role: form.role, full_name: form.full_name.trim() || null, college_id: form.college_id || null, ...numberFields(form) };
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
