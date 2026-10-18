"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), context);
context.database = database;
vm.runInContext("DB = database", context);

function evaluate(expression) {
    return vm.runInContext(expression, context);
}

const archivedPlayerIds = ["7270", "7271", "7278", "7282", "7285"];

for (const playerId of archivedPlayerIds) {
    const profile = evaluate('playerDetail("' + playerId + '")');
    const player = database.players.find(item => item.id === playerId);

    assert.ok(profile.includes("<tfoot>"), player.name + " is missing the full-total row");
    assert.ok(profile.includes("Łącznie Bosch"), player.name + " has no lifetime totals");
    assert.ok(profile.includes("Archiwalny bilans Bosch"), player.name + " needs the source label");
}

const golabeski = evaluate('playerDetail("7270")');

assert.ok(golabeski.includes("Orlik 2024"));
assert.ok(golabeski.includes("<td>—</td><td>1</td><td>1</td><td>2</td>"));
assert.ok(golabeski.includes("Niepełny podział na sezony: 13 meczów"));
assert.ok(golabeski.includes("Archiwum Boscha — najlepszy sezon"));
assert.ok(golabeski.includes("Łącznie Bosch"));

const sołowiej = evaluate('playerDetail("7285")');
assert.ok(sołowiej.includes("Tabela PLP — archiwum"));
assert.ok(sołowiej.includes("3 asyst"));

const historic2024 = evaluate('seasonPage("139")');
assert.ok(historic2024.includes("Gołąbeski Piotr"), "Known 2024 goals must appear even when appearances are unavailable");

const historic2022 = evaluate('seasonPage("120")');
assert.ok(historic2022.includes("Sołowiej Tomasz"), "Known 2022 goals must appear even when appearances are unavailable");

const historic2023 = evaluate('seasonPage("125")');
for (const name of ["Sołowiej Tomasz", "Markowski Damian", "Gorbacewicz Emil", "Kossakowski Maciej"]) {
    assert.ok(historic2023.includes(name), "Orlik 2023 should contain " + name);
}

for (const player of database.players) {
    const profile = evaluate('playerDetail("' + player.id + '")');

    assert.ok(profile.includes("<tfoot>"), "Every Bosch player must show career totals: " + player.name);
}

console.log("Verified the archived goal and assist breakdown for every Bosch player profile and historic season leaderboard.");
