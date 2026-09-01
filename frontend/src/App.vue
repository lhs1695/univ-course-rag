<template>
  <el-container>
    <el-header class="app-header" v-if="session.user">
      <div class="app-title">课程问答</div>
      <div class="app-user">
        <span>{{ session.user.username }}</span>
        <el-button v-if="isAdmin" text type="primary" @click="router.push('/admin/users')">
          用户
        </el-button>
        <el-button v-if="isAdmin" text type="primary" @click="router.push('/admin/courses')">
          课程
        </el-button>
        <el-button v-else text type="primary" @click="goCourses">我的课程</el-button>
        <el-button text @click="onLogout">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { logout, session } from "./session";

const router = useRouter();
const isAdmin = computed(() => session.user?.role === "admin");

function goCourses() {
  router.push("/courses");
}

async function onLogout() {
  try {
    await logout();
    await router.push("/login");
  } catch (error) {
    ElMessage.error(error.message);
  }
}
</script>
