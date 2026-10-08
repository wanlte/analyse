<template>
  <main class="page">
    <h1>电商数据工作台</h1>
    <div class="toolbar">
      <button :class="{ on: timeRange === '今天' }" @click="chooseRange('今天')">今天</button>
      <button :class="{ on: timeRange === '本周' }" @click="chooseRange('本周')">本周</button>
      <button :class="{ on: timeRange === '本月' }" @click="chooseRange('本月')">本月</button>
      <button :class="{ on: timeRange === '自定义' }" @click="chooseRange('自定义')">自定义</button>
      <template v-if="timeRange === '自定义'">
        <input v-model="dateFrom" type="date" @change="chooseRange('自定义')" />
        <input v-model="dateTo" type="date" @change="chooseRange('自定义')" />
      </template>
      <span class="muted">部门 {{ scope }}</span>
    </div>
    <p class="muted lede" v-if="source">数据来源 {{ source }} · 数据至 {{ dataDate }}</p>
    <p class="muted lede" v-else>先到分析页保存数据，再回来看数。</p>
    <section class="cards">
      <article
        v-for="card in cards"
        :key="card.name"
        class="card metric"
        role="button"
        tabindex="0"
        @click="openCard(card)"
        @keydown.enter="openCard(card)"
      >
        <p class="metric-name">{{ card.name }}</p>
        <span v-if="mark(card.change).anomaly" class="badge">异常</span>
        <p class="number">{{ showValue(card.value) }}</p>
        <p :class="mark(card.change).tone">{{ mark(card.change).text }}</p>
      </article>
    </section>
    <section class="card">
      <h2>我的看板</h2>
      <p v-if="boards.length === 0" class="muted">还没有保存的看板</p>
      <article v-for="item in boards" :key="item.id" class="rowline">
        <div>
          <p>{{ item.name }}</p>
          <p class="muted">{{ summary(item).range }} · {{ summary(item).line }}</p>
        </div>
        <div class="stack">
          <input v-model="names[item.id]" />
          <button @click="rename(item)">改名</button>
          <button @click="open(item.id)">回看</button>
          <button @click="again">重新分析</button>
          <button @click="share(item)">分享</button>
          <button @click="remove(item)">删除</button>
        </div>
      </article>
      <p v-if="boardNotice" class="up">{{ boardNotice }}</p>
    </section>
    <section v-if="opened" class="card">
      <h2>{{ opened.name }}</h2>
      <p>口径版本 {{ opened.metric_version }}</p>
      <p>数据日期 {{ opened.data_date }}</p>
      <ol>
        <li v-for="step in opened.steps" :key="step.name">{{ step.name }}：{{ step.detail }}</li>
      </ol>
      <p>{{ opened.answer }}</p>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api.js";
import { cardMark, cardTarget } from "../cards.js";
import { boardLink, boardSummary } from "../boardView.js";

const cards = ref([
  { name: "GMV", value: null, change: null },
  { name: "订单量", value: null, change: null },
  { name: "转化率", value: null, change: null },
  { name: "退款率", value: null, change: null },
]);
const source = ref("");
const dataDate = ref("");
const boards = ref([]);
const opened = ref(null);
const names = reactive({});
const boardNotice = ref("");
const route = useRoute();
const scope = ref("全部");
const timeRange = ref("本月");
const dateFrom = ref("");
const dateTo = ref("");
const router = useRouter();

function showValue(value) {
  return value === null || value === undefined ? "—" : value;
}

function mark(change) {
  return cardMark(change);
}

function openCard(card) {
  const target = cardTarget(card);
  router.push(target);
}

async function loadCards() {
  try {
    const body = await api("/home/cards");
    cards.value = body.cards;
    source.value = body.source;
    dataDate.value = body.data_date;
  } catch {
    source.value = "";
  }
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
  await loadCards();
}

function summary(item) {
  return boardSummary(item);
}

async function open(id) {
  opened.value = await api(`/boards/${id}`);
}

async function rename(item) {
  const name = (names[item.id] || "").trim();
  if (!name) return;
  const saved = await api(`/boards/${item.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  item.name = saved.name;
  boardNotice.value = "已改名";
}

async function remove(item) {
  await api(`/boards/${item.id}`, { method: "DELETE" });
  boards.value = boards.value.filter((board) => board.id !== item.id);
  if (opened.value && opened.value.id === item.id) opened.value = null;
}

function again() {
  router.push("/analysis");
}

async function share(item) {
  const link = boardLink(item.id, window.location.origin);
  await navigator.clipboard.writeText(link);
  boardNotice.value = "链接已复制";
}

onMounted(async () => {
  try {
    const me = await api("/me");
    scope.value = me.data_scope || "全部";
    const config = await api("/me/config");
    timeRange.value = config.default_range || "本月";
    dateFrom.value = config.date_from || "";
    dateTo.value = config.date_to || "";
  } catch {
    scope.value = "全部";
  }
  await loadCards();
  api("/boards")
    .then((items) => {
      boards.value = items;
      items.forEach((item) => {
        names[item.id] = item.name;
      });
      const boardId = Number(route.query.board);
      if (boardId) open(boardId);
    })
    .catch(() => {
      boards.value = [];
    });
});
</script>
