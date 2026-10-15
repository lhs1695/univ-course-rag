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
          <el-form class="ask-form" aria-labelledby="question-title" @submit.prevent="onAsk">
            <el-form-item>
              <el-input v-model="query" id="question-input" aria-label="课程问题" aria-describedby="question-help"
                type="textarea" :rows="4" maxlength="2000" show-word-limit
                placeholder="例如：这两个概念有什么区别？请结合课内资料说明。" />
            </el-form-item>
            <div class="composer-footer">
              <p id="question-help" class="subtle">仅依据本课资料作答；问句草稿仅保存在本页内存。</p>
              <el-button type="primary" native-type="submit" :loading="asking" :disabled="!query.trim()">
                {{ asking ? '正在组织回答' : '提问' }}
              </el-button>
            </div>
          </el-form>
        </div>

        <section class="response-panel" :aria-busy="asking" aria-labelledby="response-title">
          <div class="panel-heading"><h2 id="response-title">课内回答</h2><span v-if="result?.answer" class="status-label">已返回回答 · 请核对证据</span></div>
          <div v-if="asking" class="response-body">
            <p role="status" class="subtle">正在检索本课资料并组织回答，请稍候。</p>
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else-if="failure" class="response-body">
            <el-alert :title="failure" type="error" :closable="false" show-icon />
            <el-button :disabled="asking || !query.trim()" @click="onAsk">重试提问</el-button>
          </div>
          <div v-else-if="result?.error_code === 'NO_EVIDENCE'" class="response-body">
            <el-alert :title="result.message || '依据不足'" type="warning" :closable="false" show-icon />
            <p class="subtle">可核对资料是否已入库，或换一个更具体的问题。</p>
          </div>
          <div v-else-if="result?.error_code" class="response-body">
            <el-alert :title="result.message || '本次问答未能完成'" type="error" :closable="false" show-icon />
            <p class="subtle">请核对资料索引状态；服务或索引异常不能说明课内没有答案。</p>
          </div>
          <div v-else-if="result?.answer" class="response-body">
            <p class="subtle">引用仅登记本次提供给模型的正文，仍需核对是否支持回答；普通链接与图片按文本显示。</p>
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
          <p>下方展示模型实际看到的引用正文；每条最多 1200 字符，可能在段落中截断。请打开原资料核对上下文。PDF 尝试定位到引用页，其他格式可能下载原文件。</p>
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
  } catch (error) {
    contextFailure.value = error.message;
    ElMessage.error(error.message);
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

async function onAsk() {
  const text = query.value.trim();
  if (!text || asking.value) {
    return;
  }
  asking.value = true;
  result.value = null;
  failure.value = "";
  try {
    result.value = await api(`/courses/${courseId.value}/ask`, {
      method: "POST",
      json: { query: text },
      timeoutMs: 300000,
    });
  } catch (error) {
    failure.value = error.message;
    ElMessage.error(error.message);
  } finally {
    asking.value = false;
  }
}
</script>

<style scoped>
.ask-page { background: transparent; border: 0; padding: 2px 0 0; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, 1fr); gap: 24px; align-items: start; }
.answer-column { min-width: 0; display: grid; gap: 22px; }
.composer-panel, .response-panel, .evidence-panel { min-width: 0; background: #fff; border: 1px solid #dfe7e2; border-radius: 12px; overflow: hidden; }
.composer-panel { border-top: 3px solid #17675f; }
.panel-heading { padding: 20px 22px 0; display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 12px; }
.panel-heading h2 { margin: 0; font-size: 17px; }
.subtle, .count-label { font-size: 12px; color: #596779; }
.status-label { font-size: 11px; color: #23764e; }
.ask-form { margin: 18px 22px 20px; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.composer-footer p { margin: 0; max-width: 70%; }
.response-panel { min-height: 300px; }
.response-body { padding: 8px 22px 24px; }
.evidence-card:focus { outline: 3px solid #17675f; outline-offset: 3px; }
.workspace-empty { padding: 32px 24px 38px; }
.workspace-empty h3 { font-size: 16px; margin: 14px 0 10px; }
.workspace-empty p { margin: 0; font-size: 13px; color: #596779; line-height: 1.9; }
.empty-step { font-size: 27px; font-weight: 300; color: #7a998a; }
.evidence-panel { background: #fbfcfb; }
.evidence-scope { margin: 16px 22px; padding-bottom: 12px; border-bottom: 1px solid #e2e9e4; }
.evidence-scope p { margin: 7px 0; font-size: 12px; color: #596779; line-height: 1.75; }
.evidence-list { padding: 0 20px 20px; margin: 0; list-style: none; display: grid; gap: 14px; }
.evidence-card { padding: 18px; background: #fff; border: 1px solid #dfe7e2; border-radius: 9px; min-width: 0; }
.source-heading { display: flex; align-items: flex-start; gap: 10px; }
.source-heading h3 { margin: 0; font-size: 14px; line-height: 1.65; }
.source-number { color: #17675f; background: #edf5f0; border-radius: 5px; font-size: 12px; padding: 2px 6px; flex-shrink: 0; }
.source-page { margin: 10px 0 0; color: #596779; font-size: 12px; }
.citation-snippet { margin: 14px 0; padding-left: 12px; border-left: 2px solid #bbd0c2; color: #475569; font-size: 13px; }
.evidence-empty { padding-top: 8px; }
@media (max-width: 900px) { .workspace-grid { grid-template-columns: minmax(0, 1fr); gap: 20px; } }
@media (max-width: 500px) { .panel-heading { padding: 18px 16px 0; } .ask-form { margin: 16px; } .composer-footer { align-items: flex-start; } .response-body { padding: 6px 16px 20px; } .evidence-scope { margin: 14px 16px; } .evidence-list { padding: 0 14px 16px; } }
</style>
