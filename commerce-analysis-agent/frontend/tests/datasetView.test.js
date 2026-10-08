import assert from "node:assert/strict";
import test from "node:test";
import { contentLines } from "../src/datasetView.js";

test("saved dataset content shows columns, row count and five rows", () => {
  const lines = contentLines({
    files: {
      orders: {
        row_count: 8,
        columns: ["order_id", "pay_amount"],
        preview: [
          { order_id: "1" },
          { order_id: "2" },
          { order_id: "3" },
          { order_id: "4" },
          { order_id: "5" },
          { order_id: "6" },
        ],
      },
    },
  });
  assert.equal(lines[0], "orders · 8 行 · order_id、pay_amount");
  assert.equal(lines.length, 6);
  assert.match(lines[1], /"order_id":"1"/);
  assert.doesNotMatch(lines.join("\n"), /"order_id":"6"/);
});
