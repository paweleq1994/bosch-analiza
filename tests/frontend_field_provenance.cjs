"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(
    fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8")
);
const source = fs.readFileSync(
    path.join(root, "docs/assets/app.js"), "utf8"
);
const sandbox = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), sandbox);
sandbox.database = database;
vm.runInContext("DB=database", sandbox);

const profile = vm.runInContext('playerDetail("1960")', sandbox);
assert.ok(profile.includes("Skąd dokładnie pochodzą statystyki?"));
assert.ok(profile.includes("podlaskaliga.pl/zawodnik/moskal-pawel/"));
assert.ok(profile.includes("podlaskaliga.pl/wydarzenie/"));
assert.ok(profile.includes("Kariera PLP"));
assert.ok(profile.includes("Bosch"));
assert.ok(profile.includes("139"));
assert.ok(profile.includes("33"));

const missing = vm.runInContext('playerDetail("10321")', sandbox);
assert.ok(missing.includes("Potwierdzone minimum"));
assert.ok(missing.includes("Brak potwierdzonego pełnego bilansu"));
assert.ok(missing.includes("podlaskaliga.pl/wydarzenie/"));
assert.ok(missing.includes("Brak publicznego linku źródłowego"));

const all = vm.runInContext('sourceEvidenceLinks(["https://evil.example/","https://podlaskaliga.pl/wydarzenie/official/","https://podlaskaliga.pl/wydarzenie/official/"],"Protokół")', sandbox);
assert.ok(!all.includes("evil.example"));
assert.equal((all.match(/Protokół/g) || []).length, 1);

console.log("Per-field PLP provenance verified for complete and partial career profiles.");
