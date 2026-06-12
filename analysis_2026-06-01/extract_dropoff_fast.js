// FAST first-pass drop-off: page-view EVENTS per (version, page), 7-day window, single group.
// (counts events, not distinct sessions — fine for a first retention-curve shape; refine later)
// Run with the PLAIN URI (no &readPreference suffix):
//   mongosh "$PS_MONGO_URI" --quiet extract_dropoff_fast.js > dropoff_fast.csv

const WINDOW_DAYS = 7;
const sinceId = ObjectId.createFromTime(Math.floor((Date.now() - WINDOW_DAYS*24*3600*1000)/1000));

print("dbName=" + db.getName());   // sanity: confirms we're on heroku_8mgcnmlb, not a garbled name
print("campaignVersionId,pageSlug,events");
db.activities.aggregate([
  { $match: { _id: { $gte: sinceId }, "content.type": "page" } },
  { $group: { _id: { v: "$content.context.perspective.versionId",
                     p: "$content.context.perspective.pageSlug" }, n: { $sum: 1 } } }
], { allowDiskUse: true }).forEach(function (r) {
  if (r._id.v && r._id.p) print([String(r._id.v), String(r._id.p), r.n].join(","));
});
