"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const script = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const frontendCode = script.slice(0, script.indexOf("function route(){"));

assert.ok(frontendCode.includes("function playerPlayedSeason("));

const context = vm.createContext({});
vm.runInContext(frontendCode, context);
context.database = database;

function evaluate(expression) {
    return vm.runInContext(expression, context);
}

evaluate("DB = database");

const in2022 = evaluate('DB.players.filter(player => playerPlayedSeason(player, "120")).map(player => player.name)');
assert.equal(in2022.length, 15);
assert.equal(new Set(in2022).size, 15);
assert.ok(in2022.includes("Moskal Paweł"));
assert.ok(in2022.includes("Sołowiej Tomasz"));
assert.ok(!in2022.includes("Dawid Daniluk"));
assert.ok(!in2022.includes("Adam Malesiński"));

const inOrlik2026 = evaluate('DB.players.filter(player => playerPlayedSeason(player, "orlik-2026")).map(player => player.name)');
assert.ok(inOrlik2026.includes("Dawid Daniluk"));

const haloRecord = evaluate('playerSeasonRecord(DB.players.find(player => player.name === "Moskal Paweł"), "120")');
assert.equal(haloRecord.apps, 13);
assert.equal(haloRecord.goals, 3);

const emptyStatsCard = evaluate('playerCard(DB.players.find(player => player.name === "Sołowiej Tomasz"), "120")');
assert.ok(emptyStatsCard.includes("Hala 2022"));
assert.ok(emptyStatsCard.includes("M: 13"));
assert.ok(!emptyStatsCard.includes("Orlik 2026:"));

const historicalCard = evaluate('playerCard(DB.players.find(player => player.name === "Moskal Paweł"), "120")');
assert.ok(historicalCard.includes("M: 13 / G: 3 / A: 3"));
assert.ok(!historicalCard.includes("Orlik 2026:"));

const allPlayers = evaluate('DB.players.filter(player => !"" || playerPlayedSeason(player, "")).length');
assert.equal(allPlayers, database.players.length);

console.log("Verified season filter: Hala 2022 = 15 known Bosch players, accurate season-specific cards.");

assert.ok(inOrlik2026.includes("Jurkowicz Mateusz"));
assert.ok(inOrlik2026.includes("Kadłubowski Krzysztof"));
assert.ok(evaluate('playerCard(DB.players.find(p=>p.id==="7275"),"orlik-2026")').includes("0 występów"));
assert.ok(evaluate('DB.players.filter(p=>playerPlayedSeason(p,"144")).some(p=>p.id==="12288")'));
