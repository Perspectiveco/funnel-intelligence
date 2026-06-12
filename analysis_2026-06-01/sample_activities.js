// PII-safe activities schema sampler. Run with:
//   mongosh "$PS_MONGO_URI" --quiet sample_activities.js > activities_schema_sample.jsonl
// Emits structure only: values stripped to "<str:len>" except a safelist of structural fields.

const SAFE = new Set(["eventType","type","__t","action","event","eventName","kind","category",
  "status","state","step","stepIndex","index","position","pageIndex","slug","pageSlug",
  "pageId","page","campaignId","campaignVersionId","platform","device","deviceType",
  "browser","os","locale","language","source","medium","utm_source"]);
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

function dump(cursor, bucket) {
  cursor.forEach(function (d) {
    try {
      var o = red(EJSON.serialize(d), null, 0);   // normalize BSON -> plain JSON, then redact
      o._bucket = bucket;
      try { o._approx_created = d._id.getTimestamp().toISOString().slice(0, 10); } catch (e) {}
      print(JSON.stringify(o));
    } catch (e) {
      // never let one bad doc abort the run; emit its top-level keys instead
      try { print(JSON.stringify({ _bucket: bucket, _err: String(e).slice(0, 90), _keys: Object.keys(EJSON.serialize(d)) })); }
      catch (e2) { print(JSON.stringify({ _bucket: bucket, _err: "hard-fail" })); }
    }
  });
}

// newest 60 = guarantees CURRENT schema; oldest 40 = lets us detect drift over the years
dump(db.activities.find().sort({ _id: -1 }).limit(60), "newest");
dump(db.activities.find().sort({ _id: 1 }).limit(40), "oldest");
