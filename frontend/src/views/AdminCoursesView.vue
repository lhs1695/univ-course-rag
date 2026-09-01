<template>
  <div class="page">
    <h2>课程</h2>
    <el-form :inline="true" @submit.prevent="onCreateCourse">
      <el-form-item label="标题">
        <el-input v-model="newTitle" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="creating">创建课程</el-button>
      </el-form-item>
    </el-form>

    <el-table
      :data="courses"
      v-loading="loading"
      highlight-current-row
      @current-change="onSelectCourse"
    >
      <el-table-column prop="title" label="课程" />
    </el-table>

    <template v-if="selected">
      <h3>成员 · {{ selected.title }}</h3>
      <el-form :inline="true" @submit.prevent="onAddMember">
        <el-form-item label="用户">
          <el-select v-model="memberUserId" filterable style="width: 200px">
            <el-option
              v-for="user in bindableUsers"
              :key="user.id"
              :label="`${user.username}（${user.role}）`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="课内角色">
          <el-select v-model="memberRole" style="width: 120px">
            <el-option label="教师" value="teacher" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="adding">加入课程</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="members">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="role" label="课内角色" width="120" />
      </el-table>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const courses = ref([]);
const users = ref([]);
const members = ref([]);
const selected = ref(null);
const loading = ref(true);
const creating = ref(false);
const adding = ref(false);
const newTitle = ref("");
const memberUserId = ref("");
const memberRole = ref("student");

const bindableUsers = computed(() => {
  if (memberRole.value === "teacher") {
    return users.value.filter((user) => user.role === "teacher");
  }
  return users.value.filter((user) => user.role === "student");
});

async function loadCourses() {
  courses.value = await api("/admin/courses");
}

async function loadUsers() {
  users.value = await api("/admin/users");
}

async function loadMembers(courseId) {
  members.value = await api(`/admin/courses/${courseId}/members`);
}

onMounted(async () => {
  try {
    await Promise.all([loadCourses(), loadUsers()]);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
});

async function onSelectCourse(row) {
  selected.value = row;
  memberUserId.value = "";
  if (!row) {
    members.value = [];
    return;
  }
  try {
    await loadMembers(row.id);
  } catch (error) {
    ElMessage.error(error.message);
  }
}

async function onCreateCourse() {
  const title = newTitle.value.trim();
  if (!title) {
    return;
  }
  creating.value = true;
  try {
    const course = await api("/admin/courses", { method: "POST", json: { title } });
    newTitle.value = "";
    ElMessage.success("已创建课程");
    await loadCourses();
    selected.value = course;
    await loadMembers(course.id);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    creating.value = false;
  }
}

async function onAddMember() {
  if (!selected.value || !memberUserId.value) {
    ElMessage.warning("请选择课程和用户");
    return;
  }
  adding.value = true;
  try {
    await api(`/admin/courses/${selected.value.id}/members`, {
      method: "POST",
      json: { user_id: memberUserId.value, role: memberRole.value },
    });
    ElMessage.success("已加入课程");
    memberUserId.value = "";
    await loadMembers(selected.value.id);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    adding.value = false;
  }
}
</script>
