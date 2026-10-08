export function answerParts(text) {
  const source = text || "";
  const supportSplit = source.split("数据支撑：");
  const suggestionSplit = (supportSplit[1] || "").split("建议：");
  const conclusion = supportSplit[0].replace(/^结论：/, "").trim();
  return {
    conclusion: conclusion || source,
    support: suggestionSplit[0].trim(),
    suggestion: (suggestionSplit[1] || "").trim(),
  };
}
