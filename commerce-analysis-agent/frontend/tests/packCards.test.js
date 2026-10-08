import assert from "node:assert/strict";
import test from "node:test";
import { packCards } from "../src/packCards.js";

test("ecommerce can be entered and retail and finance stay closed", () => {
  const cards = packCards([
    { name: "电商", code: "EC_V1.0", enterable: true, metrics: ["GMV"] },
    { name: "金融", code: "FN", enterable: false },
  ]);
  const byName = Object.fromEntries(cards.map((item) => [item.name, item.status]));
  assert.equal(byName["电商"], "可进入");
  assert.equal(byName["零售"], "即将开放");
  assert.equal(byName["金融"], "即将开放");
});
