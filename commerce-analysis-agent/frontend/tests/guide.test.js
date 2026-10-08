import assert from "node:assert/strict";
import test from "node:test";
import { directionGuide, directions, overviewReset } from "../src/guide.js";

test("each direction has a hint and two follow-up questions", () => {
  assert.equal(directions.length, 4);
  for (const item of directions) {
    const guide = directionGuide(item.name);
    assert.ok(guide.hint);
    assert.equal(guide.asks.length, 2);
  }
});

test("returning to overview clears channel filters", () => {
  const next = overviewReset();
  assert.equal(next.direction, "看大盘");
  assert.equal(next.channel, "全部");
  assert.equal(next.category, "全部");
  assert.equal(next.city, "全部");
});
