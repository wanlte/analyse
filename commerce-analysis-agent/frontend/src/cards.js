export function cardMark(change) {
  if (change === null || change === undefined || Number.isNaN(Number(change))) {
    return { text: "", tone: "muted", anomaly: false };
  }
  const value = Number(change);
  const percent = `${Math.round(Math.abs(value) * 100)}%`;
  if (value > 0) return { text: `▲ ${percent} 环比`, tone: "up", anomaly: false };
  if (value < 0) return { text: `▼ ${percent} 环比`, tone: "down", anomaly: value < -0.1 };
  return { text: "0% 环比", tone: "muted", anomaly: false };
}

export function cardTarget(card) {
  const mark = cardMark(card.change);
  if (mark.anomaly) return { path: "/analysis", query: { direction: "找异常" } };
  return { path: "/analysis", query: { direction: "看结构", metric: card.name } };
}
