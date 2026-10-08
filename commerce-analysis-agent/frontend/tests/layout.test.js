import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { answerParts } from "../src/answer.js";

test("an answer splits into conclusion, support and suggestion", () => {
  const parts = answerParts("结论：GMV 上升。数据支撑：本期 80。建议：看自营。");
  assert.equal(parts.conclusion, "GMV 上升。");
  assert.equal(parts.support, "本期 80。");
  assert.equal(parts.suggestion, "看自营。");
});

test("top bar stays 56px and the page is 1200 wide", () => {
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  assert.match(css, /height:\s*56px/);
  assert.match(css, /position:\s*sticky/);
  assert.match(css, /max-width:\s*1200px/);
  assert.match(css, /max-width:\s*1024px/);
  assert.match(css, /max-width:\s*768px/);
  assert.match(css, /#2563EB/i);
  assert.match(css, /#16A34A/i);
  assert.match(css, /#DC2626/i);
});
