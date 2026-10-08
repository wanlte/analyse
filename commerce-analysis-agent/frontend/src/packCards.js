export function packCards(packs) {
  const items = packs || [];
  const ecommerce = items.find((item) => item.enterable) || { name: "电商", code: "EC_V1.0", enterable: true, metrics: [] };
  const named = new Map(items.map((item) => [item.name, item]));
  const coming = ["零售", "金融"].map((name) => named.get(name) || { name, enterable: false });
  const listed = new Set([ecommerce.name, ...coming.map((item) => item.name)]);
  const rest = items.filter((item) => !item.enterable && !listed.has(item.name));
  return [
    { ...ecommerce, status: "可进入" },
    ...coming.concat(rest).map((item) => ({ ...item, status: "即将开放" })),
  ];
}
