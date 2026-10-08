<template>
  <div>
    <header class="nav">
      <strong class="brand">电商分析</strong>
      <button class="menu" type="button" @click="menuOpen = !menuOpen">菜单</button>
      <nav :class="{ open: menuOpen }">
        <router-link v-for="item in pageRoutes" :key="item.path" :to="item.path">
          {{ item.title }}
        </router-link>
      </nav>
      <router-link class="avatar" to="/profile">
        <img v-if="avatarUrl" :src="avatarUrl" alt="" />
        <span v-else>{{ avatarText }}</span>
      </router-link>
    </header>
    <router-view />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "./api.js";
import { pageRoutes } from "./routes.js";

const avatarText = ref("");
const avatarUrl = ref("");
const menuOpen = ref(false);
const route = useRoute();

async function loadMe() {
  if (!localStorage.getItem("token")) {
    avatarUrl.value = "";
    avatarText.value = "";
    return;
  }
  try {
    const me = await api("/me");
    avatarUrl.value = me.avatar_url || "";
    avatarText.value = (me.nickname || me.username || "我").slice(0, 1);
  } catch {
    avatarText.value = "";
  }
}

onMounted(() => {
  loadMe();
  window.addEventListener("me-changed", loadMe);
});
onUnmounted(() => window.removeEventListener("me-changed", loadMe));
watch(() => route.fullPath, loadMe);
</script>
