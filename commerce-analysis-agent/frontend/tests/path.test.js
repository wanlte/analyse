import assert from "node:assert/strict";
import test from "node:test";
import { analysisPath } from "../src/path.js";

test("directions map onto overview, drill and attribution", () => {
  assert.equal(analysisPath("看大盘"), "总览");
  assert.equal(analysisPath("看趋势"), "总览");
  assert.equal(analysisPath("看结构"), "下钻");
  assert.equal(analysisPath("看大盘", "下钻到单品"), "下钻");
  assert.equal(analysisPath("找异常"), "归因");
});
