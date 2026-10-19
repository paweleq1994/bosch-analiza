"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const db = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const code = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const sandbox = vm.createContext({});
vm.runInContext(code.slice(0, code.indexOf("function route(){")), sandbox);
sandbox.DBValue = db;
vm.runInContext("DB=DBValue", sandbox);
const summary = vm.runInContext("streakMetrics(DB.matches)", sandbox);
assert.ok(summary.best.wins >= 1);
assert.ok(summary.best.unbeaten >= summary.best.wins);
assert.equal(summary.latest.length, 5);
assert.equal(summary.cleanSheets, db.matches.filter(match => match.ga === 0).length);
const chart = vm.runInContext("goalMinuteGroups(DB.matches)", sandbox);
assert.ok(chart.rows.every(row => row.count >= 0));
assert.ok(chart.unknown >= 0);
const html = vm.runInContext("enhancedHistoricalAnalysis()", sandbox);
assert.ok(html.includes("Serie i ostatnia forma"));
assert.ok(html.includes("Kiedy padały nasze gole"));
assert.ok(html.includes("Mecze bez nagrania"));
assert.ok(html.includes("Pierwsza i druga połowa"));
const officialLink="https://podlaskaliga.pl/wydarzenie/verified/";
sandbox.halfFixtures=[
    {halftime:"1:0",gf:2,ga:3,event_link:officialLink},
    {halftime:"0:0",gf:2,ga:1,event_link:officialLink},
    {halftime:"0:1",gf:1,ga:1,event_link:officialLink},
    {halftime:"",gf:4,ga:2,event_link:officialLink},
    {halftime:"3:0",gf:2,ga:1,event_link:officialLink},
    {halftime:"0:0",gf:1,ga:0,event_link:""},
];
const halves=vm.runInContext("halfTimeMetrics(halfFixtures)",sandbox);
assert.equal(halves.verified,3);
assert.equal(halves.unavailable,3);
assert.equal(halves.halves[0].gf,1);
assert.equal(halves.halves[0].ga,1);
assert.equal(halves.halves[1].gf,4);
assert.equal(halves.halves[1].ga,4);
assert.equal(halves.states[0].losses,1);
assert.equal(halves.states[1].wins,1);
assert.equal(halves.states[2].draws,1);
const historicalHalves=vm.runInContext("halfTimeMetrics(DB.matches)",sandbox);
assert.equal(historicalHalves.verified+historicalHalves.unavailable,db.matches.length);
console.log("Validated official goal minutes, historical form, clean sheets and video coverage analytics.");
