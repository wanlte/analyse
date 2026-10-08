import assert from "node:assert/strict";
import test from "node:test";
import { packSlots } from "../src/slots.js";

test("resource pack upload slots use the five Chinese names", () => {
  assert.deepEqual(
    packSlots.map((item) => item[1]),
    ["订单", "订单明细", "用户", "商品", "行为"],
  );
});
