export const pageRoutes = [
  { path: "/", title: "首页" },
  { path: "/analysis", title: "分析" },
  { path: "/packs", title: "资源包" },
  { path: "/data", title: "数据" },
  { path: "/profile", title: "个人中心" },
];

export function showDirections(datasetId) {
  return Boolean(datasetId);
}
