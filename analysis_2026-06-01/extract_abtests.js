// Causal layer: flatten campaign_ab_tests -> one line per real experiment.
// Small collection (~340K docs) -> prod-safe. Reads from secondary. IDs are not PII.
// Run: mongosh "$PS_MONGO_URI" --quiet extract_abtests.js > abtests_pairs.jsonl

try { db.getMongo().setReadPref("secondary"); } catch (e) {}

var emitted = 0;
db.campaign_ab_tests.find().forEach(function (d) {
  var t = d.abTests || {};
  for (var k in t) {
    var e = t[k];
    if (e === null || typeof e !== "object") continue;
    try {
      var o = EJSON.serialize(e);          // keep full entry: control/variant ids + any winner/status fields
      o._campaignId = String(d._id);
      o._testKey = k;                       // epoch-ms-ish key
      print(JSON.stringify(o));
      emitted++;
    } catch (err) {}
  }
});
print(JSON.stringify({ _done: true, emitted: emitted }));
