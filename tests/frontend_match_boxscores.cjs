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

const show = expression => vm.runInContext(expression, context);

assert.equal(database.matches.length, 113);
assert.equal(database.matches.filter(match => match.player_performance_source).length, 113);
assert.equal(database.matches.reduce((sum, match) => sum + match.player_performance.length, 0), 988);

const fixture = database.matches.find(match => match.id === "7416");
assert.ok(fixture.player_performance.some(player => player.player_id === "1960"));
assert.ok(show('matchDetail("7416")').includes("Oficjalny skład i statystyki meczu"));
assert.ok(show('matchDetail("7416")').includes("Moskal Paweł"));
assert.ok(show('playerDetail("1960")').includes("Występy mecz po meczu"));
assert.ok(show('playerDetail("1960")').includes("Orlik 2026"));
assert.ok(show('playerComparison()').includes("compare-player-a"));
assert.ok(show('playerComparison()').includes("compare-player-b"));
assert.ok(show('dataQuality()').includes("Niezidentyfikowane ID"));

const controls={"compare-player-a":{value:"7271"},"compare-player-b":{value:"1960"},
                "compare-player-season":{value:""},"compare-player-result":{innerHTML:""}};
context.document={getElementById:id=>controls[id]};
show("updatePlayerComparison()");
assert.ok(controls["compare-player-result"].innerHTML.includes("≥ 10"));
assert.ok(controls["compare-player-result"].innerHTML.includes("<td>G+A / mecz</td><td>—</td>"));
assert.ok(controls["compare-player-result"].innerHTML.includes("wymaga pełnego bilansu"));

fixture.goal_protocol.own_goals_conceded_scorers=[{player_id:"1960",name:"Moskal Paweł",goals:1,minutes:["18"]}];
assert.ok(show('matchDetail("7416")').includes("18′"));

console.log("Verified match box scores, 988 appearances, player timelines, comparison and data quality routes.");
