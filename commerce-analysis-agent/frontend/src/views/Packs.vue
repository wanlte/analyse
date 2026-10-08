<template>
  <main class="page">
    <h1>问数据，不用写 SQL</h1>
    <section class="pack-grid">
      <article
        v-for="pack in cards"
        :key="pack.name"
        class="card pack"
        :class="{ closed: pack.status !== '可进入' }"
        role="button"
        tabindex="0"
        @click="choose(pack)"
        @keydown.enter="choose(pack)"
      >
        <h2>{{ pack.name }}</h2>
        <p class="muted">{{ pack.metrics && pack.metrics.length ? `${pack.metrics.length} 大指标` : "覆盖订单、商品、用户" }}</p>
        <p :class="pack.status === '可进入' ? 'up' : 'muted'">{{ pack.status }}</p>
      </article>
    </section>
    <p v-if="notice" class="muted">{{ notice }}</p>
    <p class="muted">数据不出域 · 仅限内部使用</p>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api.js";
import { packCards } from "../packCards.js";

const packs = ref([]);
const notice = ref("");
const router = useRouter();
const cards = computed(() => packCards(packs.value));

function choose(pack) {
  if (pack.status !== "可进入") {
    notice.value = "敬请期待";
    return;
  }
  notice.value = "";
  router.push("/analysis");
}

onMounted(async () => {
  packs.value = await api("/resource-packs");
});
</script>
