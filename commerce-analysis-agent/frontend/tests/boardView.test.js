import assert from "node:assert/strict";
import test from "node:test";
import { boardLink, boardSummary } from "../src/boardView.js";

test("a board summary keeps the time range and the conclusion sentence", () => {
  const summary = boardSummary({
    data_date: "2026-10-02",
    answer: "结论：当时的回答。数据支撑：见读数。建议：留档。",
  });
  assert.equal(summary.range, "2026-10-02");
  assert.equal(summary.line, "当时的回答。");
  assert.equal(boardLink(4, "http://127.0.0.1:5173"), "http://127.0.0.1:5173/?board=4");
});
