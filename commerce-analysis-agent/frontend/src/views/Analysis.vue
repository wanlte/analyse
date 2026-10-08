<template>
  <main class="page">
    <h1>分析</h1>
    <section class="card">
      <div class="stack">
        <label><input v-model="usePack" type="radio" :value="true" /> 使用资源包</label>
        <label><input v-model="usePack" type="radio" :value="false" /> 不使用资源包</label>
      </div>
      <input v-model="name" class="name" placeholder="数据名称" />
      <div v-if="usePack" class="slots">
        <label v-for="[slot, label] in packSlots" :key="slot">
          <span>{{ label }}</span>
          <input type="file" @change="pick(slot, $event)" />
          <span class="muted">{{ files[slot] ? files[slot].name : "未上传" }}</span>
        </label>
      </div>
      <label v-else class="slots">
        <span>数据文件</span>
        <input type="file" @change="pick('file', $event)" />
        <span class="muted">{{ files.file ? files.file.name : "未上传" }}</span>
      </label>
      <button type="button" @click="preview">预览</button>
      <button :disabled="!canSave" @click="save">保存数据</button>
      <div v-if="previewBody">
        <p v-for="(file, slot) in previewBody.files" :key="slot">
          {{ slot }} · {{ file.row_count }} 行 · {{ (file.columns || []).join("、") }}
        </p>
        <p v-for="(row, index) in previewRows" :key="index" class="muted">{{ row }}</p>
        <p v-if="missingText" class="down">缺少 {{ missingText }}</p>
      </div>
      <p v-if="error" class="down">{{ error }}</p>
    </section>
    <section class="card">
      <h2>历史数据集</h2>
      <p v-if="datasets.length === 0" class="muted">还没有历史数据集</p>
      <p v-for="item in datasets" :key="item.id" class="rowline">
        <span>{{ item.name }} · {{ item.resource_pack || "未使用资源包" }} · {{ item.row_count }} 行</span>
        <button @click="viewContent(item.id)">查看内容</button>
        <button @click="selectedId = item.id">用于分析</button>
      </p>
      <p v-for="(line, index) in contentLines(openedContent)" :key="index" class="muted">{{ line }}</p>
    </section>
    <section v-if="showDirections(selectedId)" class="card">
      <p>正在分析的数据集 {{ selectedName }}</p>
      <div class="stack">
        <button :class="{ on: timeRange === '今天' }" @click="chooseRange('今天')">今天</button>
        <button :class="{ on: timeRange === '本周' }" @click="chooseRange('本周')">本周</button>
        <button :class="{ on: timeRange === '本月' }" @click="chooseRange('本月')">本月</button>
        <button :class="{ on: timeRange === '自定义' }" @click="chooseRange('自定义')">自定义</button>
        <template v-if="timeRange === '自定义'">
          <input v-model="dateFrom" type="date" @change="chooseRange('自定义')" />
          <input v-model="dateTo" type="date" @change="chooseRange('自定义')" />
        </template>
        <button v-if="rangeStale" @click="confirmRange">范围已变，重新分析</button>
      </div>
      <h2>你想看什么？</h2>
      <div v-if="usingPack" class="directions">
        <button
          v-for="item in directions"
          :key="item.name"
          class="direction"
          :class="{ picked: lastDirection === item.name }"
          @click="ask(item.name)"
        >
          {{ item.name }}
          <small>{{ item.hint }}</small>
        </button>
      </div>
      <div class="stack">
        <button :class="{ on: gmvMode === '含退款' }" @click="setMode('含退款')">含退款</button>
        <button :class="{ on: gmvMode === '净GMV' }" @click="setMode('净GMV')">净 GMV</button>
        <button :class="{ on: grain === '周' }" @click="setGrain('周')">周</button>
        <button :class="{ on: grain === '月' }" @click="setGrain('月')">月</button>
        <button :class="{ on: grain === '季' }" @click="setGrain('季')">季</button>
        <button :class="{ on: compareMode === '环比' }" @click="setCompare('环比')">环比</button>
        <button :class="{ on: compareMode === '同比' }" @click="setCompare('同比')">同比</button>
      </div>
      <div class="stack">
        <label class="field">渠道
          <select v-model="channel" @change="setDimension">
            <option>全部</option>
            <option v-for="item in dimensions.channel" :key="item">{{ item }}</option>
          </select>
        </label>
        <label class="field">品类
          <select v-model="category" @change="setDimension">
            <option>全部</option>
            <option v-for="item in dimensions.category" :key="item">{{ item }}</option>
          </select>
        </label>
        <label class="field">地区
          <select v-model="city" @change="setDimension">
            <option>全部</option>
            <option v-for="item in dimensions.city" :key="item">{{ item }}</option>
          </select>
        </label>
      </div>
      <div class="stack">
        <span v-if="timeRange" class="chip">{{ timeRange }}</span>
        <span v-if="channel !== '全部'" class="chip">渠道 {{ channel }}</span>
        <span v-if="category !== '全部'" class="chip">品类 {{ category }}</span>
        <span v-if="city !== '全部'" class="chip">地区 {{ city }}</span>
      </div>
      <p v-if="pending" class="muted">正在查询数据…</p>
      <p v-else-if="emptyTable" class="muted">当前条件下暂无数据</p>
      <p v-if="queryError" class="down">
        {{ queryError }}
        <button type="button" @click="ask(lastDirection, lastQuestion)">重试</button>
      </p>
      <p class="caliber">{{ timeRange }} · {{ metricDetail }}</p>
      <div ref="chartEl" class="chart"></div>
      <p v-if="note">{{ note }}</p>
      <article v-if="answer" class="conclusion">
        <p class="conclusion-line">{{ parts.conclusion }}</p>
        <p v-if="parts.support">数据支撑 <span class="number">{{ parts.support }}</span></p>
        <p v-if="parts.suggestion" class="suggest">行动建议 {{ parts.suggestion }}</p>
        <p v-if="attribution" class="muted">{{ attribution }}</p>
      </article>
      <details v-if="report">
        <summary>查看 SQL</summary>
        <p>来源 {{ sourceDetail }}</p>
        <p>口径 {{ metricDetail }}</p>
        <p class="number">{{ report.sql }}</p>
      </details>
      <div class="stack">
        <button v-for="question in activeAsks" :key="question" @click="ask(lastDirection, question)">
          {{ question }}
        </button>
      </div>
      <div class="stack">
        <input v-model="followup" placeholder="追问" />
        <button @click="ask(lastDirection, followup)">追问</button>
        <button @click="setMode('净GMV')">改看净 GMV</button>
        <button v-if="report" class="primary" @click="saveBoard">保存到看板</button>
        <button v-if="report && report.log_id" @click="vote('赞')">赞</button>
        <button v-if="report && report.log_id" @click="vote('踩')">踩</button>
      </div>
      <p v-if="notice">{{ notice }}</p>
      <p class="stepper">
        <button type="button" :class="pathClass('总览')" :disabled="!stepDone('总览')" @click="goOverview">① 总览</button>
        <span class="muted">→</span>
        <span :class="pathClass('下钻')">② 下钻</span>
        <span class="muted">→</span>
        <span :class="pathClass('归因')">③ 归因</span>
      </p>
      <h2>历史会话</h2>
      <p v-if="sessions.length === 0" class="muted">还没有历史会话</p>
      <p v-for="item in sessions" :key="item.id" class="rowline">
        <span>{{ item.question }} · {{ item.status }}</span>
        <button @click="openSession(item.id)">回看</button>
      </p>
    </section>
    <div class="examples">
      <button type="button" @click="examplesOpen = !examplesOpen">示例问题</button>
      <div v-if="examplesOpen" class="example-list">
        <button v-for="question in exampleQuestions" :key="question" type="button" @click="askGuide(question)">
          {{ question }}
        </button>
      </div>
    </div>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import * as echarts from "echarts";
import { api } from "../api.js";
import { chartNote, chartOption, labelColumn } from "../chart.js";
import { drillRequest } from "../drill.js";
import { answerParts } from "../answer.js";
import { contentLines } from "../datasetView.js";
import { packSlots } from "../slots.js";
import { rangeDecision } from "../range.js";
import { analysisPath } from "../path.js";
import { showDirections } from "../routes.js";
import { directionGuide, directions, overviewReset } from "../guide.js";

const route = useRoute();

const usePack = ref(true);
const name = ref("");
const files = ref({});
const datasets = ref([]);
const packs = ref([]);
const selectedId = ref(null);
const openedContent = ref(null);
const steps = ref([]);
const answer = ref("");
const error = ref("");
const report = ref(null);
const notice = ref("");
const preference = ref("汇总结论");
const previewBody = ref(null);
const gmvMode = ref("含退款");
const grain = ref("月");
const compareMode = ref("环比");
const timeRange = ref("本月");
const dateFrom = ref("");
const dateTo = ref("");
const rangeStale = ref(false);
const dimensions = ref({ channel: [], category: [], city: [] });
const channel = ref("全部");
const category = ref("全部");
const city = ref("全部");
const pending = ref(false);
const note = ref("");
const activeLabel = ref("");
const pathStep = computed(() => analysisPath(lastDirection.value, lastQuestion.value));
const sessions = ref([]);
const followup = ref("");
const examplesOpen = ref(false);
const queryError = ref("");
const queuedDirection = ref(String(route.query.direction || ""));
const lastDirection = ref(String(route.query.direction || "看大盘"));
const lastQuestion = ref("");
const chartEl = ref(null);
let chart;

const selected = computed(() => datasets.value.find((item) => item.id === selectedId.value) || null);
const usingPack = computed(() => Boolean(selected.value && selected.value.resource_pack));
const selectedName = computed(() => {
  if (!selected.value) return String(selectedId.value || "");
  const pack = selected.value.resource_pack || "未使用资源包";
  return `${selected.value.name} · ${pack} · ${selected.value.row_count} 行`;
});
const guideQuestions = computed(() => {
  const pack = selected.value && packs.value.find((item) => item.code === selected.value.resource_pack);
  const questions = (pack && pack.questions) || [];
  if (questions.length) return questions.slice(0, 12);
  return directions.flatMap((item) => item.asks).slice(0, 12);
});
const exampleQuestions = guideQuestions;
const activeAsks = computed(() => directionGuide(lastDirection.value).asks);
const emptyTable = computed(() => {
  const rows = report.value && report.value.table && report.value.table.rows;
  return Boolean(report.value) && (!rows || rows.length === 0);
});
const pathOrder = ["总览", "下钻", "归因"];

function pathClass(name) {
  if (pathStep.value === name && !pending.value) return "up";
  return "muted";
}

function stepDone(name) {
  return pathOrder.indexOf(name) < pathOrder.indexOf(pathStep.value);
}

async function goOverview() {
  if (!stepDone("总览")) return;
  const next = overviewReset();
  channel.value = next.channel;
  category.value = next.category;
  city.value = next.city;
  await ask(next.direction, next.question);
}

function askGuide(question) {
  let direction = "看大盘";
  if (question.includes("趋势") || question.includes("怎么变")) direction = "看趋势";
  else if (question.includes("占比") || question.includes("排名") || question.includes("结构")) direction = "看结构";
  else if (question.includes("异常") || question.includes("拖累")) direction = "找异常";
  ask(direction, question);
}

const parts = computed(() => answerParts(answer.value));

const attribution = computed(() => {
  const step = steps.value.find((item) => item.name === "计算");
  return step ? step.detail : "";
});

const sourceDetail = computed(() => steps.value.find((item) => item.name === "数据来源")?.detail || "");
const metricDetail = computed(() => steps.value.find((item) => item.name === "口径")?.detail || "");

const missingText = computed(() => {
  const missing = previewBody.value?.missing || {};
  return Object.entries(missing)
    .map(([slot, columns]) => `${slot} ${[].concat(columns).join("、")}`)
    .join("；");
});

const previewRows = computed(() => {
  const files = previewBody.value?.files || {};
  return Object.values(files).flatMap((file) => (file.preview || []).slice(0, 5));
});

const canSave = computed(() => previewBody.value && !missingText.value);

function formData(includeName) {
  const form = new FormData();
  if (includeName) form.set("name", name.value || "未命名数据");
  form.set("resource_pack", usePack.value ? "EC_V1.0" : "");
  Object.entries(files.value).forEach(([slot, file]) => form.append(slot, file));
  return form;
}

function pick(slot, event) {
  files.value[slot] = event.target.files[0];
}

async function load() {
  datasets.value = await api("/datasets");
  const requested = Number(route.query.dataset);
  if (requested) selectedId.value = requested;
}

async function viewContent(id) {
  openedContent.value = await api(`/datasets/${id}`);
}

async function preview() {
  error.value = "";
  previewBody.value = await api("/datasets/preview", { method: "POST", body: formData(false) });
}

async function save() {
  error.value = "";
  if (!canSave.value) return;
  try {
    await api("/datasets", { method: "POST", body: formData(true) });
    previewBody.value = null;
    await load();
  } catch (reason) {
    error.value = reason.message;
  }
}

async function ask(direction, question = "") {
  notice.value = "";
  queryError.value = "";
  pending.value = true;
  lastDirection.value = direction || lastDirection.value;
  lastQuestion.value = question;
  try {
    const body = await api("/analyses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: selectedId.value,
        direction: lastDirection.value,
        question,
        gmv_mode: gmvMode.value,
        grain: grain.value,
        compare: compareMode.value,
        time_range: timeRange.value,
        date_from: dateFrom.value,
        date_to: dateTo.value,
        channel: channel.value,
        category: category.value,
        city: city.value,
      }),
    });
    report.value = body;
    steps.value = body.steps;
    answer.value = body.answer;
    await loadSessions();
    await nextTick();
    draw();
  } catch (reason) {
    queryError.value = businessError(reason.message);
  } finally {
    pending.value = false;
  }
}

function businessError(message) {
  const text = message || "";
  if (text.includes("权限")) return "当前账号暂无该数据范围权限";
  if (text.includes("具体") || text.includes("不明确")) return "可以再具体一点吗？例如：上个月的 GMV 是多少";
  return "数据查询出错了，请稍后再试";
}

async function loadSessions() {
  sessions.value = await api("/analyses");
}

async function openSession(id) {
  const body = await api(`/analyses/${id}`);
  report.value = body;
  steps.value = body.steps;
  answer.value = body.answer;
  pending.value = false;
  await nextTick();
  draw();
}

async function chooseRange(next) {
  timeRange.value = next;
  await api("/me/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      default_range: timeRange.value,
      date_from: timeRange.value === "自定义" ? dateFrom.value : "",
      date_to: timeRange.value === "自定义" ? dateTo.value : "",
    }),
  });
  if (rangeDecision(Boolean(report.value)) === "confirm") rangeStale.value = true;
}

async function confirmRange() {
  rangeStale.value = false;
  if (report.value) await ask(lastDirection.value);
}

async function setMode(mode) {
  gmvMode.value = mode;
  if (report.value) await ask(lastDirection.value);
}

async function setDimension() {
  if (report.value) await ask(lastDirection.value);
}

watch(selectedId, async (id) => {
  channel.value = "全部";
  category.value = "全部";
  city.value = "全部";
  if (!id) {
    dimensions.value = { channel: [], category: [], city: [] };
    return;
  }
  dimensions.value = await api(`/datasets/${id}/dimensions`);
  if (queuedDirection.value) {
    const direction = queuedDirection.value;
    const metric = route.query.metric ? `${route.query.metric}怎么样` : "";
    queuedDirection.value = "";
    await ask(direction, metric);
  }
});

async function setCompare(next) {
  compareMode.value = next;
  if (report.value) await ask(lastDirection.value);
}

async function setGrain(next) {
  grain.value = next;
  if (report.value) await ask(lastDirection.value);
}

function draw() {
  const table = report.value && report.value.table;
  note.value = chartNote(lastQuestion.value, table && table.columns);
  activeLabel.value = labelColumn(table && table.columns);
  const option = chartOption(lastDirection.value, table, lastQuestion.value);
  if (!option || !chartEl.value) return;
  chart = chart || echarts.init(chartEl.value);
  chart.setOption(option, true);
  chart.off("click");
  chart.on("click", (params) => {
    const next = drillRequest(activeLabel.value, params.name);
    if (next.channel) channel.value = next.channel;
    if (next.category) category.value = next.category;
    if (next.time_range) {
      timeRange.value = next.time_range;
      dateFrom.value = next.date_from;
      dateTo.value = next.date_to;
    }
    ask(next.direction, next.question);
  });
}

async function saveBoard() {
  await api("/boards", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: name.value || "分析看板",
      answer: report.value.answer,
      steps: report.value.steps,
      metric_version: report.value.metric_version,
      data_date: report.value.data_date,
    }),
  });
  notice.value = "已保存到看板";
}

async function vote(choice) {
  const body = await api(`/analyses/${report.value.log_id}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vote: choice }),
  });
  notice.value = body.vote;
}

onMounted(() => {
  load().catch(() => {
    datasets.value = [];
  });
  loadSessions().catch(() => {
    sessions.value = [];
  });
  api("/resource-packs")
    .then((items) => {
      packs.value = items;
    })
    .catch(() => {
      packs.value = [];
    });
  api("/me/config")
    .then((config) => {
      preference.value = config.output_preference;
      timeRange.value = config.default_range || "本月";
      dateFrom.value = config.date_from || "";
      dateTo.value = config.date_to || "";
    })
    .catch(() => {
      preference.value = "汇总结论";
    });
});

watch(
  () => route.query.dataset,
  (value) => {
    const requested = Number(value);
    if (requested) selectedId.value = requested;
  },
);
</script>
