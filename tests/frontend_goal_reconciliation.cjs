"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const script = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const context = vm.createContext({});

vm.runInContext(script.slice(0, script.indexOf("function route(){")), context);
context.database = database;
vm.runInContext("DB = database", context);

function render(expression) {
    return vm.runInContext(expression, context);
}

const recordsPage = render("records()");
assert.ok(recordsPage.includes("Administracyjne"));
assert.ok(recordsPage.includes("Do wyjaśnienia"));
assert.ok(recordsPage.includes("https://podlaskaliga.pl/wydarzenie/ost-sport-vs-bosch-service-tech-car-2/"));
assert.ok(recordsPage.includes("Pozostała różnica: <strong>7</strong>"));
assert.ok(recordsPage.includes("Potwierdzonych bramek administracyjnych: <strong>1</strong>"));

const pietruczuk = database.players.find(player => player.name.toLowerCase().includes("pietruczuk"));
assert.ok(pietruczuk, "Pietruczuk must be visible as a Bosch scorer");
const pietruczukPage = render('playerDetail("' + pietruczuk.id + '")');
assert.ok(pietruczukPage.includes("Oficjalny protokół PLP — potwierdzone minimum"));
assert.ok(pietruczukPage.includes("≥ 1"));
assert.ok(pietruczukPage.includes("Łącznie Bosch"));

const wojciuk = database.players.find(player => player.name.toLowerCase().includes("wojciuk"));
assert.ok(wojciuk, "Wojciuk must be visible in Bosch roster");
const wojciukPage = render('playerDetail("' + wojciuk.id + '")');
assert.ok(wojciukPage.includes("5"));
assert.ok(wojciukPage.includes("2"));
assert.ok(wojciukPage.includes("orlik") || wojciukPage.includes("Orlik"));

const season2026 = render('seasonPage("orlik-2026")');
const season2025 = render('seasonPage("144")');
assert.ok(season2026.includes("Wojciuk"));
assert.ok(season2025.includes("Pietruczuk"));

console.log("Verified official scorer additions, minimum-only stats, walkover evidence and seven unresolved goals.");
