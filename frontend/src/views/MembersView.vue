<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">课程管理</p><h1>本课学生</h1><p class="page-description">{{ courseTitle }} · 维护学生的课程访问权限，移出后下一次请求即失权。</p></header>
    <p class="hint">只能加入已有学生账号，不能在这里创建用户。不改教师成员。</p>

    <el-form class="add-form" :inline="true" @submit.prevent="onAdd">
      <el-form-item label="学生账号">
        <el-input v-model="username" placeholder="已有学生用户名" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="adding">加入本课</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="students" v-loading="loading" empty-text="还没有学生">
      <el-table-column prop="username" label="用户名" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="danger" link @click="onRemove(row)">移出</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const members = ref([]);
const loading = ref(true);
const adding = ref(false);
const username = ref("");

const students = computed(() => members.value.filter((row) => row.role === "student"));

async function loadMembers() {
  members.value = await api(`/courses/${courseId.value}/members`);
}

onMounted(async () => {
  try {
    const course = await api(`/courses/${courseId.value}`);
    courseTitle.value = course.title;
    await loadMembers();
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
});

async function onAdd() {
  if (adding.value) return;
  const name = username.value.trim();
  if (!name) {
    ElMessage.warning("请输入已有学生账号");
    return;
  }
  adding.value = true;
  try {
    await api(`/courses/${courseId.value}/members`, {
      method: "POST",
      json: { username: name },
    });
    ElMessage.success("已加入本课");
    username.value = "";
    await loadMembers();
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    adding.value = false;
  }
}

async function onRemove(row) {
  try {
    await ElMessageBox.confirm(`将「${row.username}」移出本课？该生将看不到这门课。`, "确认移出", {
      type: "warning",
      confirmButtonText: "移出",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await api(`/courses/${courseId.value}/members/${row.user_id}`, { method: "DELETE" });
    ElMessage.success("已移出");
    await loadMembers();
  } catch (error) {
    ElMessage.error(error.message);
  }
}
</script>

<style scoped>
.hint {
  margin: -12px 0 16px;
  padding-left: 12px;
  border-left: 2px solid #c7d5d0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.75;
}

.add-form {
  margin-bottom: 24px;
}
</style>
