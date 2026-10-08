import { createRouter, createWebHistory } from "vue-router";
import Home from "./views/Home.vue";
import Analysis from "./views/Analysis.vue";
import Packs from "./views/Packs.vue";
import DataPage from "./views/Data.vue";
import Profile from "./views/Profile.vue";
import Login from "./views/Login.vue";
import { pageRoutes } from "./routes.js";

const views = {
  "/": Home,
  "/analysis": Analysis,
  "/packs": Packs,
  "/data": DataPage,
  "/profile": Profile,
};

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...pageRoutes.map((route) => ({
      ...route,
      component: views[route.path],
    })),
    { path: "/login", component: Login },
  ],
});

router.beforeEach((to) => {
  if (to.path !== "/login" && !localStorage.getItem("token")) return "/login";
});
