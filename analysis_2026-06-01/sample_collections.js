// PII-safe multi-collection schema sampler.
// Run: mongosh "$PS_MONGO_URI" --quiet sample_collections.js > collections_schema_sample.jsonl
// Emits, per collection: a {_collection,_count} header + newest N redacted docs (values stripped).

const COLLECTIONS = [
  "campaign_ab_tests",   // the real A/B experiments (causal layer)
  "sessionaggregations", // possible pre-computed funnel/step aggregates
  "analytics",           // possible funnel analytics / drop-off
  "interactions",        // possible per-step interaction events
  "sessions",            // prod sessions (may have more than the scrubbed BQ copy)
  "visitors",            // visitor-level (high PII risk -> heavily redacted)
  "trackingproperties",  // tracking config
  "activities"           // the 4.4B event stream (just a peek at structure)
];
const N = 6;

const SAFE = new Set(["eventType","type","__t","action","event","eventName","kind","category",
  "status","state","step","stepIndex","index","position","pageIndex","slug","pageSlug",
  "pageId","page","campaignId","campaignVersionId","platform","device","deviceType",
  "browser","os","locale","language","source","medium","utm_source","winner","variant",
  "isWinner","isControl","testStatus","metric"]);
const PII = /(email|mail|phone|tel|mobile|telefon|first.?name|last.?name|vorname|nachname|fullname|answer|values?|inputs?|message|comment|text|content|address|strasse|street|city|plz|zip|postal|contact|ip|user.?agent|payload|data)/i;
const EMAIL = /[\w.+-]+@[\w-]+\.[\w.-]+/;
const PHONE = /(\+?\d[\d\s().\/-]{6,}\d)/;

function red(v, key, depth) {
  if (depth > 7) return "<deep>";
  if (v === null || v === undefined) return v;
  if (Array.isArray(v)) return v.slice(0, 4).map(function (x) { return red(x, key, depth + 1); });
  if (typeof v === "object") {
    if ("$oid" in v) return "<oid>";
    if ("$date" in v) return "<date>";
    if ("$binary" in v) return "<bin>";
    if ("$numberLong" in v) return Number(v.$numberLong);
    if ("$numberInt" in v) return Number(v.$numberInt);
    if ("$numberDouble" in v) return Number(v.$numberDouble);
    if ("$numberDecimal" in v) return Number(v.$numberDecimal);
    var o = {};
    for (var k in v) o[k] = red(v[k], k, depth + 1);
    return o;
  }
  if (typeof v === "string") {
    if (key && PII.test(key)) return "<redacted>";
    if (EMAIL.test(v) || PHONE.test(v)) return "<pii>";
    if (key && SAFE.has(key) && v.length <= 60) return v;
    return "<str:" + v.length + ">";
  }
  return v;
}

COLLECTIONS.forEach(function (cn) {
  try {
    var cnt = db.getCollection(cn).estimatedDocumentCount();
    print(JSON.stringify({ _collection: cn, _count: cnt }));
    db.getCollection(cn).find().sort({ _id: -1 }).limit(N).forEach(function (d) {
      try {
        var o = red(EJSON.serialize(d), null, 0);
        o._collection = cn;
        try { o._approx_created = d._id.getTimestamp().toISOString().slice(0, 10); } catch (e) {}
        print(JSON.stringify(o));
      } catch (e) {
        try { print(JSON.stringify({ _collection: cn, _err: String(e).slice(0, 90), _keys: Object.keys(EJSON.serialize(d)) })); }
        catch (e2) { print(JSON.stringify({ _collection: cn, _err: "hard-fail" })); }
      }
    });
  } catch (e) {
    print(JSON.stringify({ _collection: cn, _err: "collection-fail " + String(e).slice(0, 80) }));
  }
});
