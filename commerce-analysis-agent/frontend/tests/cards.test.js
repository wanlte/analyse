import assert from "node:assert/strict";
import test from "node:test";
import { cardMark, cardTarget } from "../src/cards.js";

test("a 20 percent drop is marked abnormal and a rise uses an up arrow", () => {
  const drop = cardMark(-0.2);
  assert.equal(drop.anomaly, true);
  assert.match(drop.text, /▼ 20% 环比/);
  const rise = cardMark(0.123);
  assert.equal(rise.anomaly, false);
  assert.match(rise.text, /^▲ /);
  assert.equal(cardTarget({ name: "GMV", change: -0.2 }).query.direction, "找异常");
  assert.equal(cardTarget({ name: "订单量", change: 0.06 }).query.direction, "看结构");
});
