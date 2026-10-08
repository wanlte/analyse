<template>
  <main class="page">
    <h1>数据</h1>
    <p v-if="datasets.length === 0" class="muted">还没有历史数据集</p>
    <article v-for="item in datasets" :key="item.id" class="card">
      <h2>{{ item.name }}</h2>
      <p class="number">{{ item.row_count }} 行</p>
      <p class="muted">{{ item.resource_pack || "未使用资源包" }} · {{ item.created_at }}</p>
      <button @click="viewContent(item.id)">查看内容</button>
      <button @click="useDataset(item.id)">用于分析</button>
      <button @click="openProfile(item.id)">探查</button>
      <button @click="openLineage(item.id)">血缘</button>
    </article>
    <section v-if="openedContent" class="card">
      <h2>内容 {{ openedContent.name }}</h2>
      <p v-for="(line, index) in contentLines(openedContent)" :key="index" class="muted">{{ line }}</p>
    </section>
    <section v-if="profile" class="card">
      <h2>探查 {{ profile.name }}</h2>
      <p v-for="table in profile.tables" :key="table.table">
        {{ table.table }} {{ table.row_count }} 行 · {{ table.columns.join("、") }}
      </p>
    </section>
    <section v-if="lineage" class="card">
      <h2>血缘 {{ lineage.dataset }}</h2>
      <p v-for="item in lineage.metrics" :key="item.metric">
        {{ item.metric }} → {{ item.tables.join("、") }} → {{ item.sources.join("、") }} → {{ lineage.dataset }}
      </p>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api.js";
import { contentLines } from "../datasetView.js";

const datasets = ref([]);
const profile = ref(null);
const lineage = ref(null);
const openedContent = ref(null);
const router = useRouter();

async function viewContent(id) {
  openedContent.value = await api(`/datasets/${id}`);
}

function useDataset(id) {
  router.push({ path: "/analysis", query: { dataset: String(id) } });
}

async function openProfile(id) {
  profile.value = await api(`/datasets/${id}/profile`);
}

async function openLineage(id) {
  lineage.value = await api(`/datasets/${id}/lineage`);
}

onMounted(async () => {
  try {
    datasets.value = await api("/datasets");
  } catch {
    datasets.value = [];
  }
});
</script>
