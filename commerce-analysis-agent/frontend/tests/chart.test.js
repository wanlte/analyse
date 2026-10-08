import assert from "node:assert/strict";
import test from "node:test";
import { chartKind, chartNote, chartOption } from "../src/chart.js";

test("structure rows become a donut", () => {
  const option = chartOption("看结构", {
    columns: ["channel", "gmv"],
    rows: [
      ["自营", 80],
      ["直播", 20],
    ],
  });
  assert.equal(option.series[0].type, "pie");
  assert.deepEqual(
    option.series[0].data.map((item) => item.name),
    ["自营", "直播"],
  );
});

test("trend rows become a line", () => {
  const option = chartOption("看趋势", {
    columns: ["pay_date", "gmv"],
    rows: [["2026-10-01", 12]],
  });
  assert.equal(option.series[0].type, "line");
  assert.deepEqual(option.series[0].data, [12]);
});

test("contribution rows become a waterfall", () => {
  const option = chartOption(
    "看大盘",
    {
      columns: ["channel", "gmv"],
      rows: [
        ["自营", 80],
        ["直播", 20],
      ],
    },
    "渠道贡献",
  );
  assert.equal(chartKind("看大盘", "渠道贡献", ["channel", "gmv"]), "waterfall");
  assert.deepEqual(option.xAxis.data, ["自营", "直播"]);
  assert.deepEqual(option.series[1].data, [80, 20]);
});

test("behavior stages become a funnel", () => {
  const option = chartOption("看大盘", {
    columns: ["behavior_type", "users"],
    rows: [
      ["浏览", 10],
      ["购买", 2],
    ],
  });
  assert.equal(option.series[0].type, "funnel");
  assert.deepEqual(
    option.series[0].data.map((item) => item.name),
    ["浏览", "购买"],
  );
});

test("a loss question without stages stays a bar and says so", () => {
  const columns = ["channel", "gmv"];
  assert.equal(chartKind("看大盘", "浏览到购买的流失", columns), "bar");
  assert.equal(chartNote("浏览到购买的流失", columns), "没有流失阶段");
});

test("amounts become histogram bins", () => {
  const option = chartOption(
    "看大盘",
    {
      columns: ["pay_amount"],
      rows: [[1], [2], [3], [8]],
    },
    "用户价值分布",
  );
  assert.equal(option.series[0].data.length, 4);
  assert.equal(option.series[0].data.reduce((sum, item) => sum + item, 0), 4);
});
