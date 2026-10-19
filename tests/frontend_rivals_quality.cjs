"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const db = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), context);
context.database = db;
vm.runInContext("DB=database", context);
const evaluate = expression => vm.runInContext(expression, context);

const groups = evaluate("groupOpponentHistory(DB.matches)");
assert.ok(groups.some(group => group.id === "1566" && group.aliases.includes("Paka") && group.aliases.includes("IST Trade")));
assert.ok(groups.some(group => group.id === "4643" && group.aliases.includes("GKS Grabówka") && group.aliases.includes("ZPS Biaform SA")));
const sameNameDifferentId = groups.filter(group => group.aliases.includes("ZPS Biaform SA"));
assert.equal(sameNameDifferentId.length, 2);
assert.ok(evaluate('opponentDetail("zps biaform sa")').includes("Wybierz właściwego rywala"));
assert.ok(evaluate('opponentDetail("plp-1566")').includes("Historyczne nazwy rywala"));
assert.ok(evaluate('opponentDetail(normalized("Konceptbud"))').includes("Najskuteczniejsi przeciw rywalowi"));

const seasonPage = evaluate('seasonPage("139")');
assert.ok(seasonPage.includes("Liderzy sezonu — kanadyjka"));
assert.ok(!evaluate("records()").includes("Strzelcy — gole — statystyki częściowe"));
vm.runInContext('DB.players.push({id:"missing-case",name:"Player Without Assists",season_stats:{"139":{apps:1,goals:1,assists:null}}})', context);
assert.ok(evaluate('seasonPage("139")').includes("niepełnymi statystykami"));
for (const id of ["1594", "12286"]) {
    assert.equal(db.players.find(player => player.id === id).stats_minimum, false);
}
vm.runInContext('DB.players.push({id:"partial-case",name:"Player With Partial History",goals:1,apps:1,stats_minimum:true})', context);
const recordsPage = evaluate("records()");
assert.ok(recordsPage.includes("Strzelcy — gole — statystyki częściowe"));
assert.ok(recordsPage.includes("Potwierdzono co najmniej"));
assert.ok(recordsPage.includes("Suma zweryfikowanych sezonów PLP"));

console.log("Verified canonical rival IDs, retained renames, disambiguated same-name teams and conservative leaderboards.");
