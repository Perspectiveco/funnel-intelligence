// analyticsPage coverage by year: docs + distinct versions per year.
// Run: mongosh "$PS_MONGO_URI" --quiet diag_year.js > diag_year.jsonl
db.analytics.aggregate([
  { $match: { type: "analyticsPage" } },
  { $group: { _id: { $year: "$day" }, docs: { $sum: 1 }, versions: { $addToSet: "$campaignVersionId" } } },
  { $project: { year: "$_id", docs: 1, nVersions: { $size: "$versions" }, _id: 0 } },
  { $sort: { year: 1 } }
], { allowDiskUse: true }).forEach(function (d) { print(JSON.stringify(d)); });
