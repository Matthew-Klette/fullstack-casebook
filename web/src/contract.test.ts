import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { generate, typesPath } from "../scripts/gen-types.mjs";

describe("API contract", () => {
  it("committed schema.d.ts is exactly what api/openapi.json generates", async () => {
    const committed = readFileSync(typesPath, "utf8");
    expect(committed, "run `make types` and fix the call sites tsc reports").toBe(await generate());
  });
});
