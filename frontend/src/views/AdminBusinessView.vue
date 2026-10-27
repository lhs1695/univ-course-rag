<template>
  <div class="page">
    <header class="page-heading"><h1>学院 / 学期 / 班级</h1><p class="page-description">维护学院与学期归属，按课程管理课内名单班。学院仅用于展示，课程访问由课内授权决定。</p></header>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
    <section class="panel-card">
      <h2>{{ collegeEditingId ? '编辑学院' : '新增学院' }}</h2>
      <el-form :inline="true" :disabled="busy" @submit.prevent="saveCollege">
        <el-form-item label="学院代码"><el-input v-model="collegeForm.code" aria-label="学院代码" maxlength="64" placeholder="字母、数字、下划线或连字符" /></el-form-item>
        <el-form-item label="学院名称"><el-input v-model="collegeForm.name" aria-label="学院名称" maxlength="100" /></el-form-item>
        <el-form-item><el-button type="primary" native-type="submit" :loading="busy">保存学院</el-button><el-button v-if="collegeEditingId" @click="resetCollege">取消编辑</el-button></el-form-item>
      </el-form>
      <el-table :data="colleges" empty-text="暂无学院">
        <el-table-column prop="code" label="学院代码" /><el-table-column prop="name" label="学院名称" />
        <el-table-column label="操作"><template #default="{row}"><el-button link :disabled="busy" @click="editCollege(row)">编辑</el-button><el-button link type="danger" :disabled="busy" @click="removeCollege(row)">删除</el-button></template></el-table-column>
      </el-table>
    </section>
    <section class="panel-card">
      <h2>{{ editingId ? '编辑学期' : '新增学期' }}</h2>
      <el-form :inline="true" @submit.prevent="saveSemester">
        <el-form-item label="学期名称"><el-input v-model="form.name" :disabled="busy" maxlength="100" /></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="form.starts_on" type="date" value-format="YYYY-MM-DD" :disabled="busy" /></el-form-item>
        <el-form-item label="结束日期"><el-date-picker v-model="form.ends_on" type="date" value-format="YYYY-MM-DD" :disabled="busy" /></el-form-item>
        <el-form-item><el-button type="primary" native-type="submit" :loading="busy">保存学期</el-button><el-button v-if="editingId" @click="reset">取消编辑</el-button></el-form-item>
      </el-form>
      <el-table :data="semesters" empty-text="暂无学期">
        <el-table-column prop="name" label="学期" /><el-table-column prop="starts_on" label="开始" /><el-table-column prop="ends_on" label="结束" />
        <el-table-column label="操作"><template #default="{row}"><el-button link :disabled="busy" @click="edit(row)">编辑</el-button><el-button link type="danger" :disabled="busy" @click="remove(row)">删除</el-button></template></el-table-column>
      </el-table>
    </section>
    <section class="panel-card">
      <h2>课程归属</h2>
      <el-form :inline="true" @submit.prevent="assignSemester">
        <el-form-item label="课程"><el-select v-model="courseId" aria-label="选择课程" style="width:240px" :disabled="busy"><el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="所属学期"><el-select v-model="semesterId" clearable aria-label="所属学期" style="width:240px" :disabled="busy"><el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.id" /></el-select></el-form-item>
        <el-form-item label="所属学院"><el-select v-model="collegeId" clearable aria-label="所属学院" style="width:240px" :disabled="busy"><el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item><el-button native-type="submit" :disabled="!courseId" :loading="busy">保存课程归属</el-button></el-form-item>
      </el-form>
    </section>
    <CourseRosterPanel v-if="courseId" :key="courseId" :course-id="courseId" />
  </div>
</template>
<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import CourseRosterPanel from "../components/CourseRosterPanel.vue";
const semesters = ref([]), courses = ref([]), courseId = ref(""), semesterId = ref("");
const colleges = ref([]), collegeId = ref(""), collegeEditingId = ref("");
const collegeForm = reactive({ code: "", name: "" });
function resetCollege() { collegeEditingId.value = ""; Object.assign(collegeForm, { code: "", name: "" }); }
function editCollege(row) { collegeEditingId.value = row.id; Object.assign(collegeForm, { code: row.code, name: row.name }); }
async function saveCollege() {
  if (!/^[A-Za-z0-9_-]+$/.test(collegeForm.code.trim()) || !collegeForm.name.trim()) { failure.value = "请填写有效学院代码及学院名称。"; return; }
  await run(async () => {
    await api(`/admin/colleges${collegeEditingId.value ? '/' + collegeEditingId.value : ''}`, { method: collegeEditingId.value ? "PUT" : "POST", json: { ...collegeForm } });
    resetCollege(); await load(); ElMessage.success("学院已保存");
  });
}
async function removeCollege(row) {
  try { await ElMessageBox.confirm(`删除学院「${row.name}」？请先解除全部用户与课程的学院归属。`, "确认删除学院", { confirmButtonText: "删除", cancelButtonText: "取消" }); } catch { return; }
  await run(async () => { await api(`/admin/colleges/${row.id}`, { method: "DELETE" }); if (collegeEditingId.value === row.id) resetCollege(); await load(); ElMessage.success("学院已删除"); });
}
const editingId = ref(""), busy = ref(false), failure = ref("");
const form = reactive({ name: "", starts_on: "", ends_on: "" });
function reset() { editingId.value = ""; Object.assign(form, { name: "", starts_on: "", ends_on: "" }); }
function edit(row) { editingId.value = row.id; Object.assign(form, { name: row.name, starts_on: row.starts_on, ends_on: row.ends_on }); }
async function load() {
  [semesters.value, courses.value, colleges.value] = await Promise.all([api("/admin/semesters"), api("/admin/courses"), api("/admin/colleges")]);
  if (!courseId.value) courseId.value = courses.value[0]?.id || "";
  syncAffiliation();
}
async function run(action) {
  if (busy.value) return;
  busy.value = true; failure.value = "";
  try { await action(); } catch (error) { failure.value = error.message; } finally { busy.value = false; }
}
async function saveSemester() {
  if (!form.name.trim() || !form.starts_on || !form.ends_on || form.ends_on < form.starts_on) { failure.value = "请填写学期名称及有效起止日期。"; return; }
  await run(async () => {
    await api(`/admin/semesters${editingId.value ? '/' + editingId.value : ''}`, { method: editingId.value ? "PUT" : "POST", json: { ...form } });
    reset(); await load(); ElMessage.success("学期已保存");
  });
}
async function remove(row) {
  try { await ElMessageBox.confirm(`删除学期「${row.name}」？已关联课程的学期需先解除关联。`, "确认删除", { confirmButtonText: "删除", cancelButtonText: "取消" }); } catch { return; }
  await run(async () => { await api(`/admin/semesters/${row.id}`, { method: "DELETE" }); if (editingId.value === row.id) reset(); await load(); });
}
async function assignSemester() {
  if (!courseId.value) return;
  await run(async () => {
    await api(`/admin/courses/${courseId.value}`, { method: "PATCH", json: { semester_id: semesterId.value || null, college_id: collegeId.value || null } });
    await load(); ElMessage.success("课程归属已保存");
  });
}
function syncAffiliation() {
  const course = courses.value.find(c => c.id === courseId.value);
  semesterId.value = course?.semester_id || "";
  collegeId.value = course?.college_id || "";
}
watch(courseId, syncAffiliation);
onMounted(() => run(load));
</script>
