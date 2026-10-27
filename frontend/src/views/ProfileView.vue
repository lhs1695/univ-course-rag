<template>
  <div class="page">
    <header class="page-heading"><h1>个人资料</h1></header>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
    <section v-if="profile" class="panel-card">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="姓名">{{ profile.full_name || '未填写，请联系管理员' }}</el-descriptions-item>
        <el-descriptions-item v-if="profile.college_name" label="学院">{{ profile.college_name }}</el-descriptions-item>
        <el-descriptions-item v-if="profile.role === 'student'" label="学号">{{ profile.student_number || '未填写' }}</el-descriptions-item>
        <el-descriptions-item v-else-if="profile.role === 'teacher' || profile.employee_number" label="工号">{{ profile.employee_number || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ {student:'学生', teacher:'教师', admin:'管理员'}[profile.role] }}</el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";
const profile = ref(null), failure = ref("");
async function load() { failure.value = ""; try { profile.value = await api("/auth/profile"); } catch (error) { failure.value = error.message; } }
onMounted(load);
</script>
