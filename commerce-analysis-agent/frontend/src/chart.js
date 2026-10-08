const LABEL_COLUMNS = ["channel", "pay_date", "period", "product_id", "behavior_type", "stage"];
const VALUE_COLUMNS = ["gmv", "orders", "pay_amount", "users"];

export function labelColumn(columns) {
  return LABEL_COLUMNS.find((name) => (columns || []).includes(name)) || "";
}

export function chartOption(direction, table, question = "") {
  if (!table || !table.rows || table.rows.length === 0) return null;
  const columns = table.columns || [];
  const kind = chartKind(direction, question, columns, table.rows);
  if (kind === "histogram") return theme(histogramOption(columns, table.rows));
  const labels = labelsOf(columns, table.rows);
  const values = valuesOf(columns, table.rows);
  if (!labels || !values) return null;
  if (kind === "pie") {
    return theme({
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          label: { color: "#1F2937" },
          data: labels.map((name, index) => ({ name, value: values[index] })),
        },
      ],
    });
  }
  if (kind === "funnel") {
    return theme({
      series: [
        {
          type: "funnel",
          label: { color: "#1F2937" },
          data: labels.map((name, index) => ({ name, value: values[index] })),
        },
      ],
    });
  }
  if (kind === "waterfall") {
    let cursor = 0;
    const helper = values.map((value) => {
      const start = cursor;
      cursor += value;
      return start;
    });
    return theme({
      xAxis: { type: "category", data: labels },
      series: [
        { type: "bar", stack: "waterfall", itemStyle: { color: "transparent" }, data: helper },
        { type: "bar", stack: "waterfall", data: values },
      ],
    });
  }
  return theme({
    xAxis: { type: "category", data: labels },
    series: [{ type: kind === "line" ? "line" : "bar", data: values, smooth: kind === "line" }],
  });
}

function theme(option) {
  if (!option) return null;
  const next = {
    backgroundColor: "transparent",
    color: ["#2563EB", "#16A34A", "#D97706", "#8B5CF6", "#DC2626"],
    textStyle: { color: "#1F2937", fontFamily: "PingFang SC, Microsoft YaHei, sans-serif" },
    ...option,
  };
  if (option.xAxis) {
    next.xAxis = {
      ...option.xAxis,
      axisLabel: { color: "#6B7280" },
      axisLine: { lineStyle: { color: "#E5E7EB" } },
    };
    next.yAxis = {
      axisLabel: { color: "#6B7280" },
      splitLine: { lineStyle: { color: "#F3F4F6" } },
    };
  }
  return next;
}

export function chartKind(direction, question, columns) {
  const text = question || "";
  if (columns.includes("behavior_type") || columns.includes("stage")) return "funnel";
  if (text.includes("流失")) return "bar";
  if (direction === "看趋势") return "line";
  if (text.includes("占比") || direction === "看结构") return "pie";
  if (text.includes("贡献")) return "waterfall";
  if (text.includes("排名")) return "bar";
  if (text.includes("分布") || text.includes("价值")) return "histogram";
  return "bar";
}

export function chartNote(question, columns) {
  const text = question || "";
  const names = columns || [];
  if (text.includes("流失") && !names.includes("behavior_type") && !names.includes("stage")) {
    return "没有流失阶段";
  }
  return "";
}

function labelsOf(columns, rows) {
  const index = columns.findIndex((name) => LABEL_COLUMNS.includes(name));
  if (index < 0) return null;
  return rows.map((row) => String(row[index]));
}

function valuesOf(columns, rows) {
  const index = columns.findIndex((name) => VALUE_COLUMNS.includes(name));
  if (index < 0) return null;
  return rows.map((row) => Number(row[index]));
}

function histogramOption(columns, rows) {
  const index = columns.findIndex((name) => VALUE_COLUMNS.includes(name));
  const source = index < 0 ? rows.map((row) => Number(row[0])) : rows.map((row) => Number(row[index]));
  const numbers = source.filter((value) => !Number.isNaN(value));
  if (numbers.length < 4) return null;
  const min = Math.min(...numbers);
  const max = Math.max(...numbers);
  const width = (max - min) / 4 || 1;
  const counts = [0, 0, 0, 0];
  numbers.forEach((value) => {
    const slot = Math.min(3, Math.floor((value - min) / width));
    counts[slot] += 1;
  });
  const labels = counts.map((_, slot) => {
    const start = min + width * slot;
    return `${start}-${start + width}`;
  });
  return {
    xAxis: { type: "category", data: labels },
    series: [{ type: "bar", data: counts }],
  };
}
