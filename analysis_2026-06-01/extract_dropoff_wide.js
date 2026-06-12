// WIDE drop-off: page-view events per (version, page) over ~18 months = full coverage.
// Reads from a SECONDARY (set in-script, so the plain URI works — no &readPreference bug).
// Run: mongosh "$PS_MONGO_URI" --quiet extract_dropoff_wide.js > dropoff_wide.csv
//
// PROD NOTE: this scans ~18 months of activities (hundreds of millions of page events).
// Run off-peak. Single-pass $group (lighter than distinct-session dedup). _id range is indexed.

try { db.getMongo().setReadPref("secondary"); } catch (e) { print("readpref note: " + e); }

const WINDOW_DAYS = 540;
const sinceId = ObjectId.createFromTime(Math.floor((Date.now() - WINDOW_DAYS*24*3600*1000)/1000));

print("dbName=" + db.getName());
print("campaignVersionId,pageSlug,events");
db.activities.aggregate([
  { $match: { _id: { $gte: sinceId }, "content.type": "page" } },
  { $group: { _id: { v: "$content.context.perspective.versionId",
                     p: "$content.context.perspective.pageSlug" }, n: { $sum: 1 } } }
], { allowDiskUse: true }).forEach(function (r) {
  if (r._id.v && r._id.p) print([String(r._id.v), String(r._id.p), r.n].join(","));
});
