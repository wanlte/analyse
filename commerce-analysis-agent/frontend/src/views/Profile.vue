<template>
  <main class="page">
    <h1>个人中心</h1>
    <p>{{ form.nickname || "我" }} · {{ form.username }} · {{ form.role }}</p>
    <form class="card" @submit.prevent="save">
      <input v-model="form.nickname" placeholder="昵称" />
      <input v-model="form.email" placeholder="邮箱" />
      <input v-model="form.phone" placeholder="手机号" />
      <input v-model="form.username" placeholder="登录账号" />
      <p class="muted">角色 {{ form.role }} · 状态 {{ form.status }}</p>
      <button>保存</button>
      <p v-if="message" :class="message === '已更新' ? 'up' : 'down'">{{ message }}</p>
    </form>
    <form class="card" @submit.prevent="changePassword">
      <h2>密码</h2>
      <input v-model="currentPassword" type="password" placeholder="当前密码" />
      <input v-model="nextPassword" type="password" placeholder="新密码" />
      <button>修改密码</button>
      <p v-if="passwordMessage" :class="passwordOk ? 'up' : 'down'">{{ passwordMessage }}</p>
    </form>
    <section class="card">
      <h2>头像</h2>
      <img v-if="form.avatar_url" :src="form.avatar_url" alt="" class="avatar" />
      <p v-else class="avatar">{{ (form.nickname || "我").slice(0, 1) }}</p>
      <input type="file" accept="image/png,image/jpeg" @change="uploadAvatar" />
    </section>
    <section class="card">
      <h2>个人配置</h2>
      <p>密钥状态 {{ config.key_status }}</p>
      <p>资源包 {{ config.resource_pack }}</p>
      <input v-model="apiKey" type="password" placeholder="自有密钥" />
      <button @click="saveKey">绑定密钥</button>
      <select v-model="config.output_preference">
        <option>汇总结论</option>
        <option>结论加图表</option>
        <option>完整报告</option>
      </select>
      <input v-model="config.default_range" placeholder="默认时间范围" />
      <button @click="saveConfig">保存配置</button>
      <button @click="createGroup">建立健康度组</button>
      <p v-for="group in groups" :key="group.id">{{ group.name }}：{{ group.metrics.join("、") }}</p>
      <p>当前分类 {{ config.category || "未选" }}</p>
      <button @click="chooseCategory('交易')">交易</button>
      <button @click="chooseCategory('流量')">流量</button>
      <button @click="chooseCategory('用户')">用户</button>
      <input v-model="metricName" placeholder="指标名" />
      <input v-model="metricField" placeholder="字段名" />
      <select v-model="metricAgg">
        <option>sum</option>
        <option>count</option>
        <option>avg</option>
        <option>rate</option>
      </select>
      <button type="button" @click="createMetric">保存自建指标</button>
      <p v-for="item in userMetrics" :key="item.id">{{ item.name }} {{ item.agg }}({{ item.field_name }})</p>
      <p v-if="configMessage" class="up">{{ configMessage }}</p>
    </section>
    <section class="card">
      <h2>费用</h2>
      <p class="number">{{ usage.cost }}</p>
      <p class="muted">{{ usage.request_count }} 次请求 · {{ usage.input_tokens }} 输入 token</p>
      <p v-for="item in usage.items" :key="item.id">
        {{ item.question }}
        <button @click="openUsage(item.id)">查看</button>
      </p>
      <p v-if="opened">{{ opened.question }} · 费用 {{ opened.cost }} · {{ opened.failure_step || opened.status }}</p>
    </section>
    <button @click="logout">退出</button>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api.js";

const form = reactive({
  nickname: "",
  email: "",
  phone: "",
  username: "",
  role: "",
  status: "",
});
const config = reactive({
  key_status: "平台密钥",
  resource_pack: "EC_V1.0",
  output_preference: "汇总结论",
  default_range: "本月",
});
const message = ref("");
const savedUsername = ref("");
const configMessage = ref("");
const passwordMessage = ref("");
const passwordOk = ref(false);
const currentPassword = ref("");
const nextPassword = ref("");
const apiKey = ref("");
const groups = ref([]);
const userMetrics = ref([]);
const metricName = ref("");
const metricField = ref("");
const metricAgg = ref("sum");
const usage = reactive({ cost: 0, request_count: 0, input_tokens: 0, items: [] });
const opened = ref(null);
const router = useRouter();

onMounted(async () => {
  try {
    Object.assign(form, await api("/me"));
    savedUsername.value = form.username;
    Object.assign(config, await api("/me/config"));
    groups.value = await api("/me/groups");
    userMetrics.value = await api("/me/metrics");
    Object.assign(usage, await api("/me/usage"));
  } catch {
    groups.value = [];
  }
});

async function changePassword() {
  passwordMessage.value = "";
  try {
    await api("/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        password: nextPassword.value,
        current_password: currentPassword.value,
      }),
    });
    currentPassword.value = "";
    nextPassword.value = "";
    passwordOk.value = true;
    passwordMessage.value = "密码已更新";
  } catch (reason) {
    passwordOk.value = false;
    passwordMessage.value = reason.message;
  }
}

async function uploadAvatar(event) {
  const formData = new FormData();
  formData.set("file", event.target.files[0]);
  Object.assign(form, await api("/me/avatar", { method: "POST", body: formData }));
  window.dispatchEvent(new Event("me-changed"));
}

function logout() {
  localStorage.removeItem("token");
  router.push("/login");
}

async function save() {
  if (form.username !== savedUsername.value && !window.confirm("确认修改登录账号？")) return;
  try {
    const updated = await api("/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nickname: form.nickname,
        email: form.email,
        phone: form.phone,
        username: form.username,
      }),
    });
    Object.assign(form, updated);
    savedUsername.value = form.username;
    message.value = "已更新";
  } catch (reason) {
    message.value = reason.message;
  }
}

async function chooseCategory(name) {
  const updated = await api("/me/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category: name }),
  });
  Object.assign(config, updated);
  configMessage.value = "已选分类";
}

async function createMetric() {
  try {
    const created = await api("/me/metrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: metricName.value,
        field_name: metricField.value,
        agg: metricAgg.value,
      }),
    });
    userMetrics.value = await api("/me/metrics");
    configMessage.value = created.name;
  } catch (reason) {
    configMessage.value = reason.message;
  }
}

async function saveConfig() {
  const updated = await api("/me/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resource_pack: config.resource_pack,
      output_preference: config.output_preference,
      default_range: config.default_range,
    }),
  });
  Object.assign(config, updated);
  configMessage.value = "配置已保存";
}

async function saveKey() {
  const updated = await api("/me/key", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey.value }),
  });
  Object.assign(config, updated);
  apiKey.value = "";
  configMessage.value = "已绑定";
}

async function createGroup() {
  const group = await api("/me/groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "健康度", metrics: ["转化率", "复购率"] }),
  });
  groups.value = [...groups.value, group];
}

async function openUsage(id) {
  opened.value = await api(`/me/usage/${id}`);
}
</script>
