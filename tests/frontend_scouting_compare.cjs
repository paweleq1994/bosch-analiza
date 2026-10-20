"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "docs/assets/scouting.js"), "utf8");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/scouting.json"), "utf8"));
const nodes = {
    cmp1: {value: ""},
    cmp2: {value: ""},
    "card-team": {value: ""},
    comparison: {innerHTML: ""}
};
const context = vm.createContext({document: {getElementById: identifier => nodes[identifier]}});
vm.runInContext(source.slice(0, source.indexOf("(async()=>")), context);
context.database = database;
vm.runInContext("data=database", context);

vm.runInContext("populateSelectors()", context);
assert.equal(nodes.cmp1.value, "bosch");
assert.equal(nodes.cmp2.value, database.teams[0].id);
assert.ok(nodes.cmp1.innerHTML.includes('value="bosch"'));
assert.ok(nodes.cmp2.innerHTML.includes('value="bosch"'));
assert.ok(!nodes["card-team"].innerHTML.includes('value="bosch"'));

const selectableTeamIds = vm.runInContext("comparisonTeams().map(team => team.id)", context);
assert.ok(selectableTeamIds.includes("bosch"));
assert.equal(selectableTeamIds.length, database.teams.length + 1);

vm.runInContext("compare()", context);
assert.ok(nodes.comparison.innerHTML.includes(database.bosch.name));
assert.ok(nodes.comparison.innerHTML.includes(database.teams[0].name));
assert.ok(nodes.comparison.innerHTML.includes("Siła (0–100)"));
assert.ok(nodes.comparison.innerHTML.includes("II liga"));
assert.ok(nodes.comparison.innerHTML.includes("Orlik: stracone/mecz"));
assert.ok(nodes.comparison.innerHTML.includes("różnych klas rozgrywkowych"));

nodes.cmp1.value = database.teams[1].id;
nodes.cmp2.value = "bosch";
vm.runInContext("compare()", context);
assert.ok(nodes.comparison.innerHTML.includes(database.bosch.name));
assert.ok(nodes.comparison.innerHTML.includes(database.teams[1].name));

nodes.cmp2.value = database.teams[0].id;
vm.runInContext("compare()", context);
assert.ok(nodes.comparison.innerHTML.includes(database.teams[1].name));
assert.ok(nodes.comparison.innerHTML.includes(database.teams[0].name));
assert.ok(!nodes.comparison.innerHTML.includes(database.bosch.name));

nodes.cmp2.value = database.teams[1].id;
vm.runInContext("compare()", context);
assert.ok(nodes.comparison.innerHTML.includes("Wybierz dwa różne zespoły."));

console.log("Verified Bosch comparison, both selectors, team-only comparison, strength and duplicate selection.");
