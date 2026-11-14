// Generates src/api/schema.d.ts from ../api/openapi.json.
// Imported by the contract test, which compares the committed file with a fresh generation.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
export const specPath = resolve(here, "../../api/openapi.json");
export const typesPath = resolve(here, "../src/api/schema.d.ts");

export async function generate() {
  const spec = JSON.parse(readFileSync(specPath, "utf8"));
  const ast = await openapiTS(spec, { defaultNonNullable: false });
  return "// Generated from api/openapi.json by scripts/gen-types.mjs. Do not edit.\n" + astToString(ast);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  writeFileSync(typesPath, await generate());
  console.error(`wrote ${typesPath}`);
}
