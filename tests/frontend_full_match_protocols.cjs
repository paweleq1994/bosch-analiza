"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const frontend = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(frontend.slice(0, frontend.indexOf("function route(){")), context);
context.database = database;
vm.runInContext("DB = database", context);

function render(expression) {
    return vm.runInContext(expression, context);
}

const indexHtml = fs.readFileSync(path.join(root, "docs/index.html"), "utf8");
assert.ok(indexHtml.includes('href="#/goals"'));

const archive = render("goalsArchive()");
assert.ok(archive.includes("113 historycznych meczów"));
assert.ok(archive.includes("293"));
assert.ok(archive.includes("289"));
assert.ok(archive.includes("Samobóje rywali"));
assert.ok(archive.includes("Samobóje Boscha"));
assert.ok(archive.includes("6"));
assert.ok(archive.includes('id="filtered-goals"'));

const goalRows = render("goalMatchRows(DB.matches)");
assert.equal(goalRows.length, 113);
assert.ok(goalRows.every(row => row.length === 9));
assert.ok(goalRows.every(row => row[8].includes("podlaskaliga.pl")));

const rutkowski = database.players.find(player => player.id === "7284");
assert.ok(rutkowski);
assert.equal(database.players.filter(player => player.name.toLowerCase().includes("rutkowski")).length, 1);
assert.deepEqual(
    [rutkowski.apps, rutkowski.goals, rutkowski.assists],
    [90, 2, 7]
);

const oldProfile = render('playerDetail("13060")');
const currentProfile = render('playerDetail("7284")');
assert.equal(oldProfile, currentProfile);
assert.ok(currentProfile.includes("Historyczne profile PLP tej samej osoby"));
assert.ok(currentProfile.includes("rutkowski-mateusz-2/"));
assert.ok(currentProfile.includes("Gole mecz po meczu"));
assert.ok(currentProfile.includes("GKS Grabówka"));

const oldGoalMinutes = render('matchDetail("9755")');
assert.ok(oldGoalMinutes.includes("Klepacki Przemysław"));
assert.ok(oldGoalMinutes.includes("Minuta nieczytelna w PLP"));
assert.ok(oldGoalMinutes.includes("Oficjalny protokół PLP"));

const ownGoalMatch = render('matchDetail("7788")');
assert.ok(ownGoalMatch.includes("Samobóje rywali"));
assert.ok(ownGoalMatch.includes("Gole samobójcze rywali"));
const selfGoalMatch = render('matchDetail("7839")');
assert.ok(selfGoalMatch.includes("Samobóje zawodników Boscha"));
assert.ok(selfGoalMatch.includes("Moskal Paweł"));

const scoredMatch = render('matchDetail("7851")');
assert.ok(scoredMatch.includes("Markowski Damian"));
assert.ok(scoredMatch.includes("29′"));

const orlik2024 = render('seasonPage("139")');
assert.ok(orlik2024.includes("Sołowiej Tomasz"));
assert.ok(orlik2024.includes("Gole i protokoły wszystkich meczów"));

const records = render("records()");
assert.ok(records.includes("293 = 289"));
assert.ok(records.includes("Najszybsze gole"));
assert.ok(records.includes("Najwięcej goli jednego zawodnika w meczu"));
assert.ok(records.includes("Kontrola kompletności strzelców"));

const analysis = render("analysis()");
assert.ok(analysis.includes("Gole zawodników w kolejnych sezonach"));

const opponent = render('opponentDetail(normalized("Konceptbud"))');
assert.ok(opponent.includes("Najskuteczniejsi przeciw rywalowi"));

console.log("Verified linked 113-match goal archive, all goal views and merged goalkeeper alias.");
