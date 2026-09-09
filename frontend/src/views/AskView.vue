<template>
  <div class="page">
    <el-page-header @back="router.push('/courses')">
      <template #content>{{ courseTitle || "问答" }}</template>
    </el-page-header>
    <div v-if="isTeacher" class="ask-nav">
      <el-button text type="primary" @click="router.push(`/courses/${courseId}/documents`)">
        本课资料
      </el-button>
    </div>

    <el-form class="ask-form" @submit.prevent="onAsk">
      <el-form-item>
        <el-input
          v-model="query"
          type="textarea"
          :rows="3"
          maxlength="2000"
          show-word-limit
          placeholder="输入问题（只根据课内资料作答）"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="asking" :disabled="!query.trim()">
          提问
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="result?.error_code === 'NO_EVIDENCE' || result?.error_code === 'EMBEDDING_MISMATCH'"
      :title="result.message || '依据不足'"
      type="warning"
      :closable="false"
      show-icon
    />

    <el-card v-else-if="result?.answer" shadow="never">
      <template #header>答案</template>
      <p class="answer">{{ result.answer }}</p>
    </el-card>

    <el-card v-if="result?.citations?.length" class="cite-card" shadow="never">
      <template #header>引用</template>
      <el-table :data="result.citations">
        <el-table-column label="资料" min-width="160">
          <template #default="{ row }">
            {{ filenameOf(row.document_id) }}
          </template>
        </el-table-column>
        <el-table-column label="页" width="80">
          <template #default="{ row }">
            {{ row.page == null ? "—" : row.page }}
          </template>
        </el-table-column>
        <el-table-column label="摘录" min-width="280">
          <template #default="{ row }">
            <div class="citation-snippet">{{ row.snippet }}</div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { session } from "../session";

const route = useRoute();
const router = useRouter();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const filenames = ref({});
const query = ref("");
const asking = ref(false);
const result = ref(null);
const isTeacher = computed(() => session.user?.role === "teacher");

onMounted(async () => {
  try {
    const [course, documents] = await Promise.all([
      api(`/courses/${courseId.value}`),
      api(`/courses/${courseId.value}/documents`),
    ]);
    courseTitle.value = course.title;
    const map = {};
    for (const doc of documents) {
      map[doc.id] = doc.filename;
    }
    filenames.value = map;
  } catch (error) {
    ElMessage.error(error.message);
  }
});

function filenameOf(documentId) {
  return filenames.value[documentId] || documentId;
}

async function onAsk() {
  const text = query.value.trim();
  if (!text) {
    return;
  }
  asking.value = true;
  result.value = null;
  try {
    result.value = await api(`/courses/${courseId.value}/ask`, {
      method: "POST",
      json: { query: text },
    });
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    asking.value = false;
  }
}
</script>

<style scoped>
.ask-nav {
  margin-top: 8px;
}

.ask-form {
  margin: 20px 0 16px;
}

.answer {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.7;
}

.cite-card {
  margin-top: 16px;
}
</style>
