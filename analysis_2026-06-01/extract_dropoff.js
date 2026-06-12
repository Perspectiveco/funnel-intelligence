// Engine B extraction: per-(version,page) session reach from analyticsPage.
// PII-free (only version id, page id, session COUNT). Time-boxed ~18 months.
// Run: mongosh "$PS_MONGO_URI" --quiet extract_dropoff.js > dropoff_page_reach.csv

const SINCE = new Date(Date.now() - 1000 * 60 * 60 * 24 * 550); // ~18 months

print("campaignVersionId,pageId,sessions,days");   // header
db.analytics.aggregate([
  { $match: { type: "analyticsPage", day: { $gte: SINCE } } },
  { $project: { campaignVersionId: 1, pageId: 1,
      n: { $size: { $cond: [{ $isArray: "$sessions" }, "$sessions", []] } } } },
  { $group: { _id: { v: "$campaignVersionId", p: "$pageId" },
      s: { $sum: "$n" }, d: { $sum: 1 } } }
], { allowDiskUse: true }).forEach(function (r) {
  print([String(r._id.v), String(r._id.p), r.s, r.d].join(","));
});
