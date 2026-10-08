export function analysisPath(direction, question = "") {
  const text = question || "";
  if (direction === "看结构" || text.includes("下钻")) return "下钻";
  if (direction === "找异常") return "归因";
  return "总览";
}
