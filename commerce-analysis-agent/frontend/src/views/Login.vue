<template>
  <main class="page gate">
    <h1>{{ registering ? "注册" : "登录" }}</h1>
    <form class="card" @submit.prevent="submit">
      <input v-model="username" placeholder="登录账号" />
      <input v-model="password" type="password" placeholder="密码" />
      <button>{{ registering ? "注册并进入" : "登录" }}</button>
      <button type="button" @click="registering = !registering">
        {{ registering ? "已有账号" : "注册" }}
      </button>
      <p v-if="error" class="down">{{ error }}</p>
    </form>
  </main>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const username = ref("");
const password = ref("");
const error = ref("");
const registering = ref(false);
const router = useRouter();

async function submit() {
  error.value = "";
  if (registering.value) {
    const created = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username.value, password: password.value }),
    });
    if (!created.ok) {
      const body = await created.json().catch(() => ({}));
      error.value = body.detail || "注册失败";
      return;
    }
  }
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username.value, password: password.value }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    error.value = body.detail || "登录失败";
    return;
  }
  localStorage.setItem("token", body.access_token);
  router.push("/analysis");
}
</script>
