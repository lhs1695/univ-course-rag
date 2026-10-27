<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">我的 / 个人主页</p><h1>个人资料</h1></header>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
    <section v-if="profile" class="panel-card">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="姓名">{{ profile.full_name || '未填写，请联系管理员' }}</el-descriptions-item>
        <el-descriptions-item v-if="profile.role === 'student'" label="学号">{{ profile.student_number || '未填写' }}</el-descriptions-item>
        <el-descriptions-item v-else-if="profile.role === 'teacher' || profile.employee_number" label="工号">{{ profile.employee_number || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ {student:'学生', teacher:'教师', admin:'管理员'}[profile.role] }}</el-descriptions-item>
      </el-descriptions>
      <template v-if="profile.role === 'student'">
        <h2>所属课内名单班</h2>
        <el-table :data="profile.classes" empty-text="暂无所属课内名单班"><el-table-column prop="course_title" label="课程" /><el-table-column prop="class_name" label="班级" /></el-table>
      </template>
    </section>
    <el-button :loading="loading" @click="load">刷新资料</el-button>
  </div>
</template>
<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";
const profile = ref(null), failure = ref(""), loading = ref(false);
async function load() { loading.value = true; failure.value = ""; try { profile.value = await api("/auth/profile"); } catch (error) { failure.value = error.message; } finally { loading.value = false; } }
onMounted(load);
</script>
