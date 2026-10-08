import assert from "node:assert/strict";
import test from "node:test";
import { pageRoutes, showDirections } from "../src/routes.js";

test("five pages can be opened", () => {
  assert.deepEqual(
    pageRoutes.map((route) => route.path),
    ["/", "/analysis", "/packs", "/data", "/profile"],
  );
});

test("directions stay hidden before a dataset is chosen", () => {
  assert.equal(showDirections(null), false);
  assert.equal(showDirections(3), true);
});
