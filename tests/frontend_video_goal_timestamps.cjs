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
scope.reviewedScorer={player_id:"7285",name:"Tomasz Sołowiej",goals:2,minutes:["21","30"]};
const mixedMinutes=vm.runInContext('goalMinutes(reviewedScorer,"7814")',scope);
assert.equal((mixedMinutes.match(/youtube.com\/watch/g)||[]).length,1);
assert.ok(mixedMinutes.includes("30′"));
assert.ok(!vm.runInContext('goalMinutes(reviewedScorer,"other-match")',scope).includes("youtube.com/watch"));
scope.reviewedMatch={id:"7814",goal_protocol:{scorers:[scope.reviewedScorer],source_url:"https://podlaskaliga.pl/wydarzenie/test/"}};
const matchGoals=vm.runInContext('goalMatchTable(reviewedMatch)',scope);
assert.ok(matchGoals.includes("t=100s"));
assert.ok(matchGoals.includes("Minuta meczu / nagranie"));
assert.ok(matchGoals.includes("czas filmu może różnić się od minuty meczu"));
assert.ok(vm.runInContext('goalMinutes({...reviewedScorer,minute_uncertain:true},"7814")',scope).includes("nieczytelna"));
vm.runInContext('verifiedCue.verification_source="broadcast_commentary_captions"',scope);
assert.ok(vm.runInContext('verifiedVideoMinuteLink("7285","7814","21")',scope).includes("YouTube — komentarz"));
assert.ok(vm.runInContext('dataQuality()', scope).includes("video-goal-review-queue.md"));
scope.rejectedVideo={status:"rejected",review_reason:"Boisko odkryte zamiast hali <test>"};
const rejectedLabel=vm.runInContext("videoReviewLabel(rejectedVideo)",scope);
assert.ok(rejectedLabel.includes("Powiązanie odrzucone"));
assert.ok(rejectedLabel.includes("&lt;test&gt;"));
assert.ok(!rejectedLabel.includes("<test>"));

scope.database=JSON.parse(fs.readFileSync(path.join(root,"docs/assets/data.json"),"utf8"));
vm.runInContext("DB=database",scope);
const zubryGoals=vm.runInContext('goalMatchTable(DB.matches.find(match=>match.id==="orlik26-2"))',scope);
assert.equal((zubryGoals.match(/youtube.com\/watch/g)||[]).length,9);
const zubryClips=vm.runInContext('verifiedGoalVideos(DB.matches.filter(match=>match.id==="orlik26-2"))',scope);
assert.ok(zubryClips.includes("Obejrzane akcje: 9"));
assert.ok(zubryClips.includes("1:53"));
assert.ok(!zubryClips.includes("4wmjAbdBHl4"));
assert.equal(vm.runInContext('verifiedGoalVideos([])',scope),"");
const allClips=vm.runInContext('verifiedGoalVideos(DB.matches)',scope);
assert.ok(allClips.includes("Komentarz gola — napisy automatyczne"));
assert.ok(allClips.includes("Obejrzana akcja"));

console.log("Verified reviewed goal links in profiles, match tables, records and filtered footage list; unreviewed minutes stay unlinked.");
