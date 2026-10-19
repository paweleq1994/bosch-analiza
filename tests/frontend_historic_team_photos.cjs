"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const scope = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), scope);
scope.database = database;
vm.runInContext("DB=database", scope);
const html = vm.runInContext('playerDetail("2204")', scope);

assert.ok(html.includes("Historyczne zdjęcia dawnych drużyn — do weryfikacji"));
assert.ok(html.includes("Osoba na zdjęciu niepotwierdzona"));
assert.ok(html.includes("Znienacka"));
assert.ok(html.includes("Nie są one liczone jako zdjęcia profilowe"));
assert.ok(html.includes("https://podlaskaliga.pl/wp-content/uploads/"));
console.log("Verified historical team photos are never presented as identified player portraits.");
