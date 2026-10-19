"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const database = JSON.parse(
    fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8")
);
const source = fs.readFileSync(
    path.join(root, "docs/assets/app.js"), "utf8"
);
const scope = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), scope);
scope.database = database;
vm.runInContext("DB=database", scope);

const moskal = vm.runInContext('playerDetail("1960")', scope);
assert.ok(moskal.includes("Pochodzenie każdej statystyki"));
assert.ok(moskal.includes("Oficjalny HTML wszystkich rozgrywek"));
assert.ok(moskal.includes("https://podlaskaliga.pl/zawodnik/moskal-pawel/"));
assert.ok(moskal.includes("Bosch"));
assert.ok(moskal.includes("PLP cała kariera"));

const privateProfile = vm.runInContext('playerDetail("10321")', scope);
assert.ok(privateProfile.includes("Pochodzenie każdej statystyki"));
assert.ok(privateProfile.includes("Brak pełnego publicznego bilansu"));
assert.ok(privateProfile.includes("https://podlaskaliga.pl/wydarzenie/"));

const review = vm.runInContext("dataQuality()", scope);
assert.ok(review.includes("reports/player-source-reconciliation.md"));
const archival = vm.runInContext('playerDetail("7271")', scope);
assert.ok(archival.includes("Superpuchar 2022"));
assert.ok(archival.includes("Archiwalny profil PLP (Internet Archive)"));
assert.ok(archival.includes("https://web.archive.org/web/20230607185424id_/"));
assert.ok(archival.includes("Brak pełnego publicznego bilansu"));

console.log("Verified Bosch/whole-PLP per-field provenance, private player sources and quality report.");

const provenance = vm.runInContext('playerProvenanceSection(DB.players.find(p=>p.id==="1960"))', scope);
assert.equal((provenance.match(/href="https:\/\/podlaskaliga.pl\/zawodnik\/moskal-pawel\//g)||[]).length,1);
assert.ok(!provenance.includes("Protokoły lub profil Bosch"));
assert.ok(!provenance.includes("Oficjalny link"));
assert.ok(provenance.includes("Wykluczenia po dwóch żółtych"));
