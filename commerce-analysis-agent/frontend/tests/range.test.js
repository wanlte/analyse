import assert from "node:assert/strict";
import test from "node:test";
import { rangeDecision } from "../src/range.js";

test("a finished report waits for confirmation before another analysis", () => {
  assert.equal(rangeDecision(true), "confirm");
  assert.equal(rangeDecision(false), "idle");
});
