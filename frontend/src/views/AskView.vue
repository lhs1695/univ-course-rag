<template>
  <div class="page ask-page" :aria-label="`课程问答：${courseTitle}`">
    <header class="page-heading">
      <p class="eyebrow">学习工作台</p>
      <h1>把疑问带回课内资料</h1>
      <p class="page-description">提出具体问题，阅读回答，再在右侧核对引用。所有内容仍需结合原资料判断。</p>
    </header>

    <div class="workspace-grid">
      <section class="answer-column" aria-label="提问与回答">
        <div class="composer-panel">
          <div class="panel-heading"><h2 id="question-title">你的问题</h2><span class="subtle">一次聚焦一个疑问</span></div>
          <el-form class="ask-form" aria-labelledby="question-title" @submit.prevent="submitQuestion">
            <el-form-item>
              <el-input v-model="query" id="question-input" aria-label="课程问题" aria-describedby="question-help"
                type="textarea" :rows="4" maxlength="2000" show-word-limit
                placeholder="例如：这两个概念有什么区别？请结合课内资料说明。" />
            </el-form-item>
            <div class="composer-footer">
              <p id="question-help" class="subtle">仅依据本课资料作答；问句草稿仅保存在本页内存。</p>
              <el-button type="primary" native-type="submit" :loading="asking" :disabled="asking || !query.trim()">
                {{ asking ? '正在组织回答' : '提问' }}
              </el-button>
            </div>
          </el-form>
        </div>

        <section class="response-panel" :aria-busy="asking" aria-labelledby="response-title">
          <div class="panel-heading"><h2 id="response-title">课内回答</h2><span v-if="result?.answer" class="status-label">已返回回答 · 请核对证据</span></div>
          <p v-if="submittedQuery" class="submitted-question"><strong>本次问题：</strong>{{ submittedQuery }}</p>
          <div v-if="asking" class="response-body">
            <p role="status" class="subtle">正在检索本课资料并组织回答，请稍候。</p>
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else-if="failure" class="response-body">
            <el-alert :title="failure" type="error" :closable="false" show-icon />
            <el-button :disabled="asking" @click="retryQuestion">重试本次问题</el-button>
          </div>
          <div v-else-if="result?.error_code === 'NO_EVIDENCE'" class="response-body">
            <el-alert title="课内资料依据不足，暂时无法据此回答。" type="warning" :closable="false" show-icon />
            <p class="subtle">这不表示系统故障。可核对课程资料是否齐全，或换一个更具体的问题。</p>
          </div>
          <div v-else-if="result?.error_code" class="response-body">
            <el-alert :title="answerFailureMessage" type="error" :closable="false" show-icon />
            <p class="subtle">本次回答未能完成，不能据此判断课内资料是否有答案。</p>
          </div>
          <div v-else-if="result?.answer" class="response-body">
            <p class="subtle">请结合引用核对回答是否有依据，并打开原资料核对。</p>
            <AnswerBody :answer="result.answer" :citations="result.citations" @citation="focusCitation" />
          </div>
          <div v-else class="workspace-empty">
            <span class="empty-step" aria-hidden="true">01</span>
            <h3>从一个具体问题开始</h3>
            <p>回答会显示在这里。系统可能依据不足，也可能出错，引用用于帮助你回到原文核对。</p>
          </div>
        </section>
      </section>

      <aside class="evidence-panel" aria-labelledby="evidence-title">
        <div class="panel-heading"><h2 id="evidence-title">核对证据</h2><span class="count-label">{{ result?.citations?.length || 0 }} 条引用</span></div>
        <div class="evidence-scope">
          <p v-if="loadingContext" role="status">正在读取本课资料状态…</p>
          <template v-else-if="contextFailure"><p>{{ contextFailure }}</p><el-button text @click="loadContext">重新加载资料信息</el-button></template>
          <template v-else><p>当前 {{ readyDocumentCount }} 份资料已入库</p><p v-if="readyDocumentCount === 0">暂无成功入库资料，可先到“课程资料”核对。</p></template>
          <p>引用摘录可能不完整，请打开原资料核对上下文。PDF 链接尝试定位到引用页。</p>
        </div>
        <ol v-if="result?.citations?.length" class="evidence-list">
          <li v-for="(citation, index) in result.citations" :key="citation.chunk_id" :id="`source-${citation.chunk_id}`" class="evidence-card" tabindex="-1" :aria-label="`引用 ${index + 1}：${filenameOf(citation.document_id)}`">
            <div class="source-heading"><span class="source-number">{{ String(index + 1).padStart(2, '0') }}</span><h3>{{ filenameOf(citation.document_id) }}</h3></div>
            <p v-if="citation.page != null" class="source-page">第 {{ citation.page }} 页</p>
            <blockquote class="citation-snippet">{{ citation.snippet }}</blockquote>
            <el-link :href="citationUrl(citation)" target="_blank" rel="noopener" type="primary" :aria-label="`查看原资料：${filenameOf(citation.document_id)}（新窗口）`">查看原资料 ↗</el-link>
          </li>
        </ol>
        <div v-else class="workspace-empty evidence-empty">
          <span class="empty-step" aria-hidden="true">02</span>
          <h3>{{ result || failure ? '本次没有可展示的引用' : '引用会显示在这里' }}</h3>
          <p>有引用的回答会列出资料名称、可用页码与摘录，便于逐条核对。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { session } from "../session";
import { questionDraft } from "../drafts";
import AnswerBody from "../components/AnswerBody.vue";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const filenames = ref({});
const loadingContext = ref(true);
const contextFailure = ref("");
const documents = ref([]);
const readyDocumentCount = computed(() => documents.value.filter(doc => doc.job_status === "succeeded").length);
const userId = session.user.id;
const query = ref(questionDraft(userId, courseId.value));
watch(query, value => questionDraft(userId, courseId.value, value), { flush: "sync" });
const asking = ref(false);
const result = ref(null);
const failure = ref("");
const submittedQuery = ref("");
const answerFailureMessage = "暂时无法完成这次回答，请稍后重试。";

async function loadContext() {
  loadingContext.value = true;
  try {
    const [course, rows] = await Promise.all([
      api(`/courses/${courseId.value}`),
      api(`/courses/${courseId.value}/documents`),
    ]);
    courseTitle.value = course.title;
    documents.value = rows;
    const map = {};
    for (const doc of rows) {
      map[doc.id] = doc.filename;
    }
    filenames.value = map;
    contextFailure.value = "";
  } catch {
    contextFailure.value = "暂时无法读取课程资料，请稍后重试。";
    ElMessage.error(contextFailure.value);
  } finally {
    loadingContext.value = false;
  }
}
onMounted(loadContext);

function filenameOf(documentId) {
  return filenames.value[documentId] || documentId;
}

function focusCitation(id) {
  if (!result.value?.citations?.some(item => item.chunk_id === id)) return;
  const card = document.getElementById(`source-${id}`);
  card?.focus({ preventScroll: true });
  card?.scrollIntoView({ block: 'nearest' });
}

function citationUrl(citation) {
  const filename = filenameOf(citation.document_id).toLowerCase();
  if (filename.endsWith(".pdf") && citation.page != null) {
    return `${citation.content_url}#page=${citation.page}`;
  }
  return citation.content_url;
}

function submitQuestion() {
  const text = query.value.trim();
  if (text) askQuestion(text);
}

function retryQuestion() {
  if (submittedQuery.value) askQuestion(submittedQuery.value);
}

async function askQuestion(text) {
  if (asking.value) return;
  submittedQuery.value = text;
  asking.value = true;
  result.value = null;
  failure.value = "";
  try {
    result.value = await api(`/courses/${courseId.value}/ask`, {
      method: "POST",
      json: { query: text },
      timeoutMs: 300000,
    });
  } catch {
    failure.value = answerFailureMessage;
    ElMessage.error(answerFailureMessage);
  } finally {
    asking.value = false;
  }
}
</script>

<style scoped>
.ask-page { padding-top: 2px; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(300px, .85fr); gap: 28px; align-items: start; }
.answer-column { min-width: 0; display: grid; gap: 24px; }
.composer-panel, .response-panel, .evidence-panel { min-width: 0; background: #fff; border: 1px solid #dfe7e2; border-radius: 12px; overflow: hidden; }
.composer-panel { border-top: 4px solid #17675f; box-shadow: 0 12px 30px rgba(28, 78, 68, .08); }
.panel-heading { padding: 21px 22px 0; display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 12px; }
.panel-heading h2 { margin: 0; font-size: 18px; font-weight: 700; }
.subtle, .count-label { font-size: 12px; color: #65736e; line-height: 1.7; }
.status-label { font-size: 12px; color: #4d7165; }
.ask-form { margin: 18px 22px 22px; }
.ask-form :deep(.el-textarea__inner) { min-height: 118px !important; padding: 13px 14px; line-height: 1.7; border-radius: 9px; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.composer-footer p { margin: 0; max-width: 70%; }
.composer-footer .el-button { min-width: 94px; min-height: 40px; }
.response-panel { min-height: 300px; }
.submitted-question { margin: 16px 22px 0; padding: 3px 0 3px 12px; border-left: 3px solid #c8d8d2; color: #56665f; font-size: 13px; line-height: 1.75; overflow-wrap: anywhere; }
.submitted-question strong { color: #41564e; font-weight: 600; }
.response-body { padding: 10px 22px 24px; line-height: 1.8; }
.response-body > .subtle { margin: 8px 0 16px; }
.evidence-card:focus { outline: 3px solid #17675f; outline-offset: 3px; }
.workspace-empty { padding: 28px 24px 34px; }
.workspace-empty h3 { font-size: 15px; margin: 8px 0 8px; font-weight: 600; }
.workspace-empty p { margin: 0; max-width: 640px; font-size: 12.5px; color: #68766f; line-height: 1.8; }
.empty-step { font-size: 11px; font-weight: 600; letter-spacing: 1.5px; color: #8a9b94; }
.evidence-panel { background: #f8faf9; border-color: #e3e9e6; position: sticky; top: 20px; max-height: calc(100vh - 40px); overflow-y: auto; }
.evidence-panel .panel-heading { padding-top: 19px; }
.evidence-panel .panel-heading h2 { font-size: 16px; font-weight: 650; }
.evidence-scope { margin: 14px 22px 16px; padding-bottom: 13px; border-bottom: 1px solid #e2e9e4; }
.evidence-scope p { margin: 5px 0; font-size: 12px; color: #6b7873; line-height: 1.7; }
.evidence-list { padding: 0 20px 22px; margin: 0; list-style: none; display: grid; gap: 12px; }
.evidence-card { padding: 14px 15px; background: rgba(255, 255, 255, .7); border: 0; border-left: 3px solid #b7cec5; border-radius: 0 7px 7px 0; min-width: 0; }
.source-heading { display: flex; align-items: flex-start; gap: 10px; }
.source-heading h3 { margin: 0; font-size: 14px; font-weight: 600; line-height: 1.6; }
.source-number { color: #487167; font-size: 11px; font-weight: 600; padding-top: 2px; flex-shrink: 0; }
.source-page { margin: 7px 0 0 30px; color: #718079; font-size: 12px; }
.citation-snippet { margin: 12px 0; padding-left: 12px; border-left: 1px solid #ccd9d4; color: #53635d; font-size: 13px; line-height: 1.75; }
.evidence-card .el-link { font-size: 13px; }
.evidence-empty { padding-top: 8px; }
@media (max-width: 900px) { .workspace-grid { grid-template-columns: minmax(0, 1fr); gap: 20px; } .evidence-panel { position: static; max-height: none; overflow-y: visible; } }
@media (max-width: 500px) { .panel-heading { padding: 18px 16px 0; } .ask-form { margin: 16px; } .composer-footer { flex-direction: column; align-items: stretch; } .composer-footer p { max-width: none; } .composer-footer .el-button { width: 100%; } .submitted-question { margin: 14px 16px 0; } .response-body { padding: 6px 16px 20px; } .evidence-scope { margin: 14px 16px; } .evidence-list { padding: 0 14px 16px; } }
</style>
