// GENTLE batched drop-off: one month of page-view events at a time, 15s pause between batches.
// Reads from secondary, _id-indexed window per month. Ctrl-C anytime — partial data is still usable.
// Run TONIGHT / off-peak:
//   mongosh "$PS_MONGO_URI" --quiet extract_dropoff_batched.js > dropoff_wide.csv
// CSV rows start with a 24-hex versionId; progress lines start with "#" (filter on parse).

try { db.getMongo().setReadPref("secondary"); } catch (e) {}

var MONTHS = 18;
var DAY = 24 * 3600 * 1000;
print("campaignVersionId,pageSlug,events,months_ago");
for (var mAgo = MONTHS; mAgo >= 1; mAgo--) {
  var lo = ObjectId.createFromTime(Math.floor((Date.now() - mAgo * 30 * DAY) / 1000));
  var hi = ObjectId.createFromTime(Math.floor((Date.now() - (mAgo - 1) * 30 * DAY) / 1000));
  var t0 = Date.now(), rows = 0;
  db.activities.aggregate([
    { $match: { _id: { $gte: lo, $lt: hi }, "content.type": "page" } },
    { $group: { _id: { v: "$content.context.perspective.versionId",
                       p: "$content.context.perspective.pageSlug" }, n: { $sum: 1 } } }
  ], { allowDiskUse: true }).forEach(function (r) {
    if (r._id.v && r._id.p) { print([String(r._id.v), String(r._id.p), r.n, mAgo].join(",")); rows++; }
  });
  print("# batch month-" + mAgo + " done, " + rows + " rows, " + Math.round((Date.now() - t0) / 1000) + "s");
  sleep(15000);   // 15s pause to keep load gentle; Ctrl-C here is safe
}
print("# ALL DONE");
