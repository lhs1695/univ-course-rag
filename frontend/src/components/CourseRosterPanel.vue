<template>
  <section class="panel-card">
    <h2>班级与名单</h2>
    <p>CSV 使用 UTF-8，表头为「学号,姓名,班级」。先由管理员维护学生账号、学号与姓名；导入只加入当前课程。重复学号全部拒绝，已在同班的学生跳过；换班请先移出课程再导入。</p>
    <el-form :inline="true" @submit.prevent="saveClass">
      <el-form-item label="班级名称"><el-input v-model="className" :disabled="busy" maxlength="100" /></el-form-item>
      <el-form-item><el-button native-type="submit" :loading="busy">{{ editingId ? '保存班级' : '新增班级' }}</el-button><el-button v-if="editingId" @click="cancelEdit">取消编辑</el-button></el-form-item>
    </el-form>
    <el-table :data="classes" empty-text="暂无班级；也可通过名单自动建立本课班级">
      <el-table-column prop="name" label="班级" /><el-table-column prop="student_count" label="学生数" />
      <el-table-column label="操作"><template #default="{row}"><el-button link :disabled="busy" @click="editClass(row)">编辑</el-button><el-button link type="danger" :disabled="busy || row.student_count > 0" @click="removeClass(row)">删除空班</el-button></template></el-table-column>
    </el-table>
    <el-form @submit.prevent="importRoster">
      <el-form-item label="CSV 名单"><input :key="courseId" type="file" accept=".csv,text/csv" :disabled="busy" aria-label="CSV 名单" @change="file = $event.target.files[0] || null; summary = null" /></el-form-item>
      <el-button type="primary" native-type="submit" :disabled="!file" :loading="busy">导入本课名单</el-button>
    </el-form>
    <div v-if="summary" role="status">
      <p>共 {{ summary.total }} 行；导入 {{ summary.imported }}，已在同班 {{ summary.unchanged }}，拒绝 {{ summary.rejected }}。</p>
      <ul v-if="summary.errors.length"><li v-for="issue in summary.errors" :key="issue.line">第 {{ issue.line }} 行：{{ issueNames[issue.code] || issue.code }}</li></ul>
    </div>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { ElMessageBox } from "element-plus";
import { api } from "../api";
const props = defineProps({ courseId: { type: String, required: true } });
const emit = defineEmits(["imported"]);
const classes = ref([]), className = ref(""), editingId = ref(""), busy = ref(false);
const file = ref(null), summary = ref(null), failure = ref("");
const issueNames = { empty_row: "空行", invalid_fields: "字段缺失或列数错误", field_too_long: "字段过长", duplicate_student_number: "名单内学号重复", student_account_missing: "学生账号不存在，请由管理员补建学号与姓名", not_student: "该账号不是学生", name_mismatch: "姓名与账号不符", membership_conflict: "已在其他班级或课内角色冲突，请核对后移出再导入" };
const path = () => `/courses/${props.courseId}/classes`;
async function load() { classes.value = await api(path()); }
function cancelEdit() { editingId.value = ""; className.value = ""; }
function editClass(row) { editingId.value = row.id; className.value = row.name; }
async function run(action) {
  if (busy.value) return;
  busy.value = true; failure.value = "";
  try { await action(); } catch (error) { failure.value = error.message; }
  finally { busy.value = false; }
}
async function saveClass() {
  if (!className.value.trim()) return;
  await run(async () => {
    await api(`${path()}${editingId.value ? '/' + editingId.value : ''}`, { method: editingId.value ? "PUT" : "POST", json: { name: className.value.trim() } });
    cancelEdit(); await load();
  });
}
async function removeClass(row) {
  try { await ElMessageBox.confirm(`删除空班「${row.name}」？`, "确认删除", { confirmButtonText: "删除", cancelButtonText: "取消" }); } catch { return; }
  await run(async () => { await api(`${path()}/${row.id}`, { method: "DELETE" }); await load(); });
}
async function importRoster() {
  if (!file.value) return;
  await run(async () => {
    summary.value = null;
    const formData = new FormData(); formData.append("file", file.value);
    summary.value = await api(`/courses/${props.courseId}/roster`, { method: "POST", formData });
    await load(); emit("imported");
  });
}
onMounted(() => run(load));
watch(() => props.courseId, () => { cancelEdit(); file.value = null; summary.value = null; run(load); });
</script>
