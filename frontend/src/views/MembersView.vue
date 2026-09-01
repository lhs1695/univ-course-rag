<template>
  <div class="page">
    <el-page-header @back="router.push('/courses')">
      <template #content>{{ courseTitle ? `本课学生 · ${courseTitle}` : "本课学生" }}</template>
    </el-page-header>
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
      <el-table-column label="" width="120">
        <template #default="{ row }">
          <el-button type="danger" link @click="onRemove(row)">移出</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

const route = useRoute();
const router = useRouter();
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
  margin: 16px 0 8px;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.add-form {
  margin: 16px 0;
}
</style>
