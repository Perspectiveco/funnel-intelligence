// Component-type counts for the pages used in A/B tests (control + variant).
// Uses the components collection (componentType is a top-level field -> no recursion).
// Batched indexed $in lookups by pageId -> light, prod-safe. Reads secondary. Emits COUNTS only.
// Run: mongosh "$PS_MONGO_URI" --quiet extract_abtest_pagefeats.js > abtest_pagefeats.csv

try { db.getMongo().setReadPref("secondary"); } catch (e) {}

// 0. safety: is pageId indexed on components? (if not, abort — would scan 59.8M)
var idx = db.components.getIndexes().map(function (i) { return Object.keys(i.key).join("+"); });
print("INDEXES " + JSON.stringify(idx));
var hasPageIdx = idx.some(function (k) { return k === "pageId" || k.indexOf("pageId") === 0; });
print("HAS_PAGEID_INDEX " + hasPageIdx);

// 1. collect distinct control+variant pageIds from campaign_ab_tests
var need = {};
db.campaign_ab_tests.find({}, { abTests: 1 }).forEach(function (d) {
  var t = d.abTests || {};
  for (var k in t) {
    var e = t[k];
    if (e === null || typeof e !== "object") continue;
    if (e.controlPageId) need[String(e.controlPageId)] = 1;
    if (e.variantPageId) need[String(e.variantPageId)] = 1;
  }
});
var ids = Object.keys(need);
print("DISTINCT_PAGEIDS " + ids.length);
if (!hasPageIdx) { print("ABORT_NO_INDEX (would scan whole collection — skipping)"); quit(); }

// 2. batched componentType counts; report match coverage
print("pageId,n_components,q_media,q_text,q_choice,q_form,inputs,buttons,social,media");
var B = 3000, matched = 0;
for (var i = 0; i < ids.length; i += B) {
  var batch = ids.slice(i, i + B).map(function (s) { return ObjectId(s); });
  var page = {};
  db.components.aggregate([
    { $match: { pageId: { $in: batch } } },
    { $group: { _id: { p: "$pageId", ct: "$componentType" }, n: { $sum: 1 } } }
  ], { allowDiskUse: true }).forEach(function (r) {
    var p = String(r._id.p), ct = r._id.ct || "", q = r.n;
    if (!page[p]) page[p] = { n: 0, qm: 0, qt: 0, qc: 0, qf: 0, inp: 0, btn: 0, soc: 0, med: 0 };
    var o = page[p]; o.n += q;
    if (ct === "questionMedia") o.qm += q;
    else if (ct === "questionText" || ct === "questionTextAnswer") o.qt += q;
    else if (ct === "questionMultipleChoice") o.qc += q;
    else if (ct === "questionForm" || ct === "form") o.qf += q;
    else if (ct === "input") o.inp += q;
    else if (ct === "button") o.btn += q;
    else if (ct === "reviews" || ct === "sliderTestimonial" || ct === "logos") o.soc += q;
    else if (ct === "media" || ct === "sliderImage" || ct === "headerImage") o.med += q;
  });
  for (var p in page) {
    matched++;
    var o = page[p];
    print([p, o.n, o.qm, o.qt, o.qc, o.qf, o.inp, o.btn, o.soc, o.med].join(","));
  }
}
print("MATCHED_PAGES " + matched + " / " + ids.length);
