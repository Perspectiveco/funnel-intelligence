// Engine B (LIVE drop-off) from activities. PII-free output: versionId, pageSlug, distinct sessions.
// PROD-SAFE design:
//   - _id range time-box uses the _id index (ObjectId is time-ordered) -> does NOT scan all 4.4B
//   - matches only content.type="page" (page views)
//   - RUN AGAINST A SECONDARY: append ?readPreference=secondary to your URI
//   - START SHORT: WINDOW_DAYS=30 first to gauge runtime/load, then widen
//
// Run: mongosh "$PS_MONGO_URI&readPreference=secondary" --quiet extract_dropoff_activities.js > dropoff_activities.csv
//   (use ?readPreference=secondary if your URI has no query string yet)

const WINDOW_DAYS = 30;   // <-- start at 30, widen to 180/365 once you've seen the load
const sinceMs = Date.now() - WINDOW_DAYS * 24 * 60 * 60 * 1000;
const sinceId = ObjectId.createFromTime(Math.floor(sinceMs / 1000));  // indexed range bound

print("campaignVersionId,pageSlug,sessions");
db.activities.aggregate([
  { $match: { _id: { $gte: sinceId }, "content.type": "page" } },
  // stage 1: dedupe to one row per (version, page, session)
  { $group: { _id: {
      v: "$content.context.perspective.versionId",
      p: "$content.context.perspective.pageSlug",
      s: "$content.context.perspective.perspectiveSessionId" } } },
  // stage 2: count distinct sessions per (version, page)
  { $group: { _id: { v: "$_id.v", p: "$_id.p" }, sessions: { $sum: 1 } } }
], { allowDiskUse: true }).forEach(function (r) {
  if (r._id.v && r._id.p) print([String(r._id.v), String(r._id.p), r.sessions].join(","));
});
