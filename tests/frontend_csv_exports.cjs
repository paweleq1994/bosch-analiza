"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const script = fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "app.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(script.slice(0, script.indexOf("function route(){")), context);
const markup = vm.runInContext('table(["Zawodnik","Gole"],[["Moskal", "3"]])', context);

assert.ok(!markup.includes("data-export-csv"));
assert.ok(markup.includes("Zawodnik"));
assert.ok(!script.includes("function exportVisibleTable(button)"));
assert.ok(!script.includes("text/csv"));
console.log("Tables retain their data without CSV export controls.");
