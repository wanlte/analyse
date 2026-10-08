export function drillRequest(column, label) {
  if (column === "pay_date" || column === "period") {
    const span = periodSpan(label);
    return {
      direction: "看趋势",
      question: `下钻 ${label}`,
      time_range: "自定义",
      date_from: span.from,
      date_to: span.to,
    };
  }
  const request = {
    direction: "看结构",
    question: column === "product_id" ? `下钻到单品 ${label}` : `下钻 ${label}`,
    channel: column === "channel" ? label : "全部",
    category: column === "category" ? label : "全部",
  };
  return request;
}

function periodSpan(label) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(label)) return { from: label, to: label };
  if (/^\d{4}-\d{2}$/.test(label)) {
    const [year, month] = label.split("-").map(Number);
    const last = new Date(year, month, 0).getDate();
    return { from: `${label}-01`, to: `${label}-${String(last).padStart(2, "0")}` };
  }
  return { from: label, to: label };
}
