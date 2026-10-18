"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const sorting = require("../docs/assets/table-sort.js");

function check(first, second, direction, expected) {
    assert.equal(
        Math.sign(sorting.compareSortValues(sorting.parseSortValue(first), sorting.parseSortValue(second), direction)),
        expected,
        first + " versus " + second,
    );
}

check("12", "9", "asc", 1);
check("1 234,50", "42,7", "asc", 1);
check("2026-10-18", "2025-04-01", "desc", -1);
check("18.10.2026", "19.10.2025", "asc", 1);
check("Jurkowicz", "Moskal", "asc", -1);
check("3:2", "2:1", "desc", -1);
check("—", "12", "asc", 1);
check("—", "12", "desc", 1);
check("10", "10", "asc", 0);

const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), context);
context.database = database;
vm.runInContext("DB = database", context);

const seasonContent = vm.runInContext('seasonPage("orlik-2026")', context);
const leaderArea = seasonContent.split("Liderzy sezonu — kanadyjka (G+A)")[1].split("Porównanie z innymi sezonami")[0];
const moskal = leaderArea.indexOf("Moskal Paweł");
const kuzma = leaderArea.indexOf("Kuźma Piotr");
assert.ok(moskal >= 0 && kuzma >= 0, "Both players should be present");
assert.ok(moskal < kuzma, "Five points must rank above four points");
assert.ok(leaderArea.includes("<th>G+A</th>"));

for (const filename of ["index.html", "scouting.html", "orlik-2026.html", "archive.html"]) {
    const html = fs.readFileSync(path.join(root, "docs", filename), "utf8");
    assert.ok(html.includes('src="assets/table-sort.js"'), filename + " should load table sorting");
}

console.log("Verified dates, Polish decimals, ties, missing values, site-wide table scripts, and Moskal above Kuźma.");
