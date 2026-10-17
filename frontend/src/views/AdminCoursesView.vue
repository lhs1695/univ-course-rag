<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">管理后台</p><h1>课程与授权</h1><p class="page-description">创建、重命名或删除课程，选择课程行管理成员。管理员访问课程内容也需显式加入。</p></header>
    <el-form :inline="true" @submit.prevent="onCreateCourse">
      <el-form-item label="标题">
        <el-input v-model="newTitle" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="creating">创建课程</el-button>
      </el-form-item>
    </el-form>

    <el-table
      ref="courseTable"
      row-key="id"
      :data="courses"
      v-loading="loading"
      empty-text="暂无课程，可先创建一门课程"
      highlight-current-row
      @current-change="onSelectCourse"
    >
      <el-table-column prop="title" label="课程" min-width="120" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link :disabled="courseBusy" @click.stop="onRenameCourse(row)">重命名</el-button>
          <el-button type="danger" link :disabled="courseBusy" @click.stop="onDeleteCourse(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <template v-if="selected">
      <h3>成员 · {{ selected.title }}</h3>
      <el-form :inline="true" @submit.prevent="onAddMember">
        <el-form-item label="用户">
          <el-select v-model="memberUserId" filterable style="width: 200px">
            <el-option
              v-for="user in bindableUsers"
              :key="user.id"
              :label="`${user.username}（${{ student: '学生', teacher: '教师', admin: '管理员' }[user.role] || user.role}）`"
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
        <el-table-column label="课内角色" width="120"><template #default="{ row }">{{ row.role === 'teacher' ? '教师' : '学生' }}</template></el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="danger" link @click="onRemoveMember(row)">移出</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

const courses = ref([]);
const courseTable = ref(null);
const courseBusy = ref(false);
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
    return users.value.filter((user) => ["teacher", "admin"].includes(user.role));
  }
  return users.value.filter((user) => ["student", "admin"].includes(user.role));
});

async function loadCourses(selectedId = selected.value?.id) {
  courses.value = await api("/admin/courses");
  const row = courses.value.find(course => course.id === selectedId) || null;
  await onSelectCourse(row);
  await nextTick();
  courseTable.value?.setCurrentRow(row);
}

async function loadUsers() {
  users.value = await api("/admin/users");
}

async function loadMembers(courseId) {
  const rows = await api(`/admin/courses/${courseId}/members`);
  if (selected.value?.id === courseId) members.value = rows;
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
  if (row?.id && row.id === selected.value?.id) {
    selected.value = row;
    return;
  }
  selected.value = row;
  members.value = [];
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
  if (creating.value) return;
  const title = newTitle.value.trim();
  if (!title) {
    return;
  }
  creating.value = true;
  try {
    const course = await api("/admin/courses", { method: "POST", json: { title } });
    newTitle.value = "";
    ElMessage.success("已创建课程");
    await loadCourses(course.id);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    creating.value = false;
  }
}

async function onRenameCourse(row) {
  if (courseBusy.value) return;
  courseBusy.value = true;
  try {
    let value;
    try {
      ({ value } = await ElMessageBox.prompt("请输入新的课程名称", "重命名课程", {
        inputValue: row.title,
        inputValidator: value => Boolean(value?.trim()) || "课程名称不能为空",
        confirmButtonText: "保存", cancelButtonText: "取消",
      }));
    } catch {
      return;
    }
    await api(`/admin/courses/${row.id}`, { method: "PATCH", json: { title: value.trim() } });
    ElMessage.success("已重命名课程");
    await loadCourses(row.id);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    courseBusy.value = false;
  }
}

async function onDeleteCourse(row) {
  if (courseBusy.value) return;
  courseBusy.value = true;
  try {
    try {
      await ElMessageBox.confirm(`删除课程「${row.title}」将移除成员与课内数据，且不可从本页恢复。确定删除？`, "确认删除课程", {
        confirmButtonText: "删除课程", cancelButtonText: "取消", type: "warning",
      });
    } catch {
      return;
    }
    await api(`/admin/courses/${row.id}`, { method: "DELETE" });
    await onSelectCourse(null);
    courseTable.value?.setCurrentRow();
    ElMessage.success("已删除课程");
    await loadCourses();
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    courseBusy.value = false;
  }
}

async function onAddMember() {
  if (adding.value) return;
  if (!selected.value || !memberUserId.value) {
    ElMessage.warning("请选择课程和用户");
    return;
  }
  adding.value = true;
  const courseId = selected.value.id;
  try {
    await api(`/admin/courses/${courseId}/members`, {
      method: "POST",
      json: { user_id: memberUserId.value, role: memberRole.value },
    });
    ElMessage.success("已加入课程");
    memberUserId.value = "";
    await loadMembers(courseId);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    adding.value = false;
  }
}

async function onRemoveMember(row) {
  const courseId = selected.value?.id;
  if (!courseId) return;
  try {
    await ElMessageBox.confirm(`将「${row.username}」移出本课？`, "确认移出", {
      confirmButtonText: "移出", cancelButtonText: "取消", type: "warning",
    });
  } catch {
    return;
  }
  try {
    await api(`/admin/courses/${courseId}/members/${row.user_id}`, { method: "DELETE" });
    if (selected.value?.id === courseId) await loadMembers(courseId);
    ElMessage.success("已移出课程");
  } catch (error) {
    ElMessage.error(error.message);
  }
}
</script>
