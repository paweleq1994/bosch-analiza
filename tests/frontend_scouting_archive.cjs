"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "docs/assets/scouting.js"), "utf8");
const db = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/scouting.json"), "utf8"));
const nodes = {};
const context = vm.createContext({document: {getElementById: id => nodes[id]}});
vm.runInContext(source.slice(0, source.indexOf("(async()=>")), context);
context.database = db;
vm.runInContext("data=database", context);
const evaluate = expression => vm.runInContext(expression, context);

const team = db.teams.find(t => t.name === "Biuro Serwis-Kopiarki");
nodes["card-team"] = {value: team.id};
nodes["pre-match"] = {};
nodes.detail = {scrollIntoView() {}};
nodes["close-detail"] = {};
evaluate("matchCard()");
evaluate(`detailed(${JSON.stringify(team.id)})`);
for (const html of [nodes["pre-match"].innerHTML, nodes.detail.innerHTML]) {
    assert.ok(html.includes("Archiwum meczów Bosch — Biuro Serwis-Kopiarki"));
    assert.ok(html.includes("Bramki Bosch : rywal"));
    for (const match of team.h2h.matches) {
        assert.ok(html.includes(match.season));
        assert.ok(html.includes(match.opponent));
        assert.ok(html.includes(`index.html#/match/${match.id}`));
        assert.ok(html.includes(match.event_link));
    }
}

// Switching opponents replaces the archive and retains the former club name.
const renamed = db.teams.find(t => t.name === "Soccer Auto Wygoda");
nodes["card-team"].value = renamed.id;
evaluate("matchCard()");
assert.ok(nodes["pre-match"].innerHTML.includes("Archiwum meczów Bosch — Soccer Auto Wygoda"));
assert.ok(nodes["pre-match"].innerHTML.includes("Aptel"));
assert.ok(!nodes["pre-match"].innerHTML.includes("Biuro Serwis-Kopiarki"));

context.team = {name: '<script>test</script>', h2h: {games: 0, matches: []}};
assert.ok(evaluate("matchArchive(team)").includes("Brak bezpośrednich meczów w archiwum Boscha."));
assert.ok(!evaluate("matchArchive(team)").includes("<script>"));
context.team = {...renamed, h2h: {...team.h2h, matches: team.h2h.matches.slice().reverse()}};
const sorted = evaluate("matchArchive(team)");
assert.ok(sorted.indexOf(team.h2h.matches[0].date) < sorted.indexOf(team.h2h.matches[1].date));
console.log("Verified scouting archives, opponent switching, renamed clubs, source links and empty state.");
