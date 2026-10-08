import assert from "node:assert/strict";
import test from "node:test";
import { drillRequest } from "../src/drill.js";

test("clicking a channel drills into that channel", () => {
  const request = drillRequest("channel", "自营");
  assert.equal(request.direction, "看结构");
  assert.equal(request.channel, "自营");
  assert.match(request.question, /下钻/);
});

test("clicking a month narrows the time window", () => {
  const request = drillRequest("period", "2026-10");
  assert.equal(request.time_range, "自定义");
  assert.equal(request.date_from, "2026-10-01");
  assert.equal(request.date_to, "2026-10-31");
});
