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
assert.ok(profile.includes("Rozwój zawodnika sezon po sezonie"));
assert.ok(profile.includes("Bramki (tylko potwierdzone sezony)"));
assert.ok(profile.includes("Asysty (tylko potwierdzone sezony)"));
assert.ok(profile.includes("G+A / mecz"));

const missing = vm.runInContext('playerTrendSection({season_history:[]})', sandbox);
assert.ok(missing.includes("Brak wystarczających źródłowych statystyk"));

const partial = vm.runInContext('playerTrendRows({season_history:[{name:"Sample",apps:2,goals:1,assists:null}]})', sandbox);
assert.equal(partial.length, 1);
assert.equal(partial[0].rate, null);

const quality = vm.runInContext("dataQuality()", sandbox);
assert.ok(quality.includes("bosch-kompendium.xlsx"));
assert.ok(quality.includes("Pobierz pełne kompendium XLSX"));

console.log("Verified per-season source-aware trend charts, missing-value semantics and XLSX archive link.");
