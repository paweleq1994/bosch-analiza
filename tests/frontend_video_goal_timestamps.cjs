"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const db = JSON.parse(fs.readFileSync(path.join(root, "docs/assets/data.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const scope = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("function route(){")), scope);
scope.database = db;
vm.runInContext("DB=database", scope);

const withoutReview = vm.runInContext('verifiedVideoMinuteLink("7285","7814","21")', scope);
assert.ok(withoutReview.includes("21′"));
assert.ok(!withoutReview.includes("youtube.com/watch"));

const cue = {
    match_id: "7814",
    player_id: "7285",
    minute: "21",
    url: "https://www.youtube.com/watch?v=hcfb9Ttmswo&t=100s",
};
scope.verifiedCue = cue;
vm.runInContext("DB.analysis.verified_goal_video_cues=[verifiedCue]", scope);
const withReview = vm.runInContext('verifiedVideoMinuteLink("7285","7814","21")', scope);
assert.ok(withReview.includes("t=100s"));
assert.ok(withReview.includes("YouTube"));
assert.ok(vm.runInContext('dataQuality()', scope).includes("video-goal-review-queue.md"));

console.log("Verified exact video link appears only after a source-confirmed timestamp record.");
