"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");

const controls = {
    "player-sort": {value: "name"},
    "player-stat-filter": {value: "all"},
    "video-sort": {value: "newest"},
};

const context = vm.createContext({
    document: {getElementById: controlId => controls[controlId] || null},
});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), context);
context.database = database;

function evaluate(code) {
    return vm.runInContext(code, context);
}

evaluate("DB = database");

const alphabetic = evaluate('sortPlayerItems(DB.players,"").map(player=>player.name)');
const expectedAlphabetic = database.players.map(player=>player.name).sort((first, second) =>
    first.localeCompare(second, "pl", {sensitivity: "base"})
);
assert.deepEqual(Array.from(alphabetic), expectedAlphabetic);

controls["player-sort"].value = "points";
const scoring = evaluate('sortPlayerItems(DB.players,"").map(player=>player.name)');
assert.ok(scoring.length > 0);
assert.ok(scoring.includes("Moskal Paweł"));

controls["player-stat-filter"].value = "scored";
const hallPlayers = evaluate('sortPlayerItems(DB.players.filter(player=>playerPlayedSeason(player,"120")),"120")');
assert.equal(hallPlayers.filter(player => player.name === "Dawid Daniluk").length, 0);
assert.ok(hallPlayers.every(player => player.season_stats?.["120"]?.goals > 0 || player.season_history?.some(
    row => row.sid === "120" && row.goals > 0
)));

const matches = evaluate('sortVideos([{title:"Older",date:"2025-01-01"},{title:"Recent",date:"2026-10-01"},{title:"Unknown",date:""}],"newest").map(video=>video.title)');
assert.deepEqual(Array.from(matches), ["Recent", "Older", "Unknown"]);
const oldest = evaluate('sortVideos([{title:"Older",date:"2025-01-01"},{title:"Recent",date:"2026-10-01"},{title:"Unknown",date:""}],"oldest").map(video=>video.title)');
assert.deepEqual(Array.from(oldest), ["Older", "Recent", "Unknown"]);

const recordPage = evaluate("records()");
for (const phrase of [
    "Kanadyjka",
    "Asysty",
    "Żółte kartki",
    "Bezpośrednie czerwone",
    "MVP",
    "Rekordy sezonowe",
    "Kontrola kompletności strzelców",
]) {
    assert.ok(recordPage.includes(phrase), phrase);
}
assert.ok(recordPage.includes("Jurkowicz Mateusz"));
assert.ok(recordPage.includes("Moskal Paweł"));

console.log("Verified alphabetical player sorting, season filters, video chronology and expanded Bosch records.");

const mixed=evaluate('sortVideos([{title:"May",date:"20250501"},{title:"June",date:"2025-06-17"},{title:"2026",date:"",match_id:"orlik26-14"}],"newest").map(v=>v.title)');
assert.deepEqual(Array.from(mixed),["2026","June","May"]);
assert.ok(evaluate('videoDateLabel({date:"",match_id:"orlik26-14"})').includes("Mecz:"));

const visibleIds=Array.from(evaluate('visibleVideos().map(v=>v.id)'));
for(const ignored of ["mRNWenMq9DA","jYIcEGA7gns","O3mBzeS-9VY","PDHzxceI8wU","8SF7bbYDS30"])assert.ok(!visibleIds.includes(ignored));
for(const pending of ["ip4f5qE7-Cs","2TgTJHeWd4o","o4tWJ0ngczs"]){
    assert.ok(visibleIds.includes(pending));
    assert.ok(evaluate(`videoReviewLabel(DB.videos.find(v=>v.id==="${pending}"))`).includes("rozgrywki do potwierdzenia"));
}
