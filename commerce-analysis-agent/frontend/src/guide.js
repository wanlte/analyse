export const directions = [
  { name: "看大盘", hint: "整体表现如何", asks: ["哪个渠道贡献最大", "下钻到单品"] },
  { name: "看趋势", hint: "时间走势变化", asks: ["哪个品类拉动了增长", "周末与工作日差异大吗"] },
  { name: "看结构", hint: "品类渠道占比", asks: ["这个品类主要由哪些渠道贡献", "环比变化最大的是哪个"] },
  { name: "找异常", hint: "指标异动提醒", asks: ["异常最可能的直接原因是什么", "去年同期表现如何"] },
];

export function directionGuide(name) {
  return directions.find((item) => item.name === name) || directions[0];
}

export function overviewReset() {
  return { direction: "看大盘", channel: "全部", category: "全部", city: "全部", question: "" };
}
