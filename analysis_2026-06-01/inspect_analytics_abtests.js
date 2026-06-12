// Inspect analytics sub-types + sessions[] sizing, and a LIVE campaign_ab_tests entry.
// Run: mongosh "$PS_MONGO_URI" --quiet inspect_analytics_abtests.js > inspect_analytics_abtests.jsonl

const SAFE = new Set(["type","analyticsType","__t","action","event","eventName","kind","category",
  "status","state","step","stepIndex","index","position","slug","pageSlug","pageId","page",
  "campaignId","campaignVersionId","winner","variant","isWinner","isControl","testStatus","metric",
  "originalVersionId","challengerVersionId","variantId","versionId","weight","split","trafficSplit",
  "name","fieldType","interactionType","analyticsType"]);
const PII = /(email|mail|phone|tel|mobile|telefon|first.?name|last.?name|vorname|nachname|fullname|answer|values?|inputs?|message|comment|content|address|strasse|street|city|plz|zip|postal|contact|ip|user.?agent)/i;
const EMAIL=/[\w.+-]+@[\w-]+\.[\w.-]+/; const PHONE=/(\+?\d[\d\s().\/-]{6,}\d)/;
function red(v,key,depth){
  if(depth>8) return "<deep>";
  if(v===null||v===undefined) return v;
  if(Array.isArray(v)) return v.slice(0,3).map(x=>red(x,key,depth+1));
  if(typeof v==="object"){
    if("$oid" in v) return "<oid>";
    if("$date" in v) return "<date>";
    if("$numberLong" in v) return Number(v.$numberLong);
    if("$numberInt" in v) return Number(v.$numberInt);
    if("$numberDouble" in v) return Number(v.$numberDouble);
    const o={}; for(const k in v) o[k]=red(v[k],k,depth+1); return o;
  }
  if(typeof v==="string"){
    if(key&&PII.test(key)) return "<redacted>";
    if(EMAIL.test(v)||PHONE.test(v)) return "<pii>";
    if(key&&SAFE.has(key)&&v.length<=60) return v;
    return "<str:"+v.length+">";
  }
  return v;
}

// 1) analytics: distribution of (type, analyticsType) + max sessions[] size
print(JSON.stringify({_section:"analytics_type_distribution"}));
db.analytics.aggregate([
  {$group:{_id:{type:"$type",at:"$analyticsType"}, n:{$sum:1},
           maxSessions:{$max:{$size:{$ifNull:["$sessions",[]]}}},
           avgSessions:{$avg:{$size:{$ifNull:["$sessions",[]]}}}}},
  {$sort:{n:-1}}
],{allowDiskUse:true}).forEach(d=>print(JSON.stringify(d)));

// 2) one redacted example of each analytics type
print(JSON.stringify({_section:"analytics_examples"}));
db.analytics.aggregate([{$group:{_id:"$type", doc:{$first:"$$ROOT"}}}],{allowDiskUse:true})
  .forEach(d=>{ var o=red(EJSON.serialize(d.doc),null,0); o._exampleOf=String(d._id); print(JSON.stringify(o)); });

// 3) campaign_ab_tests: show up to 5 docs that actually have a non-null abTests entry
print(JSON.stringify({_section:"abtests_live"}));
var shown=0;
db.campaign_ab_tests.find().sort({updatedAt:-1}).limit(400).forEach(function(d){
  if(shown>=5) return;
  var t=d.abTests||{};
  var nn=Object.keys(t).filter(function(k){return t[k]!==null;});
  if(nn.length){
    shown++;
    var entry=red(EJSON.serialize(t[nn[0]]),null,0);
    print(JSON.stringify({campaignDocId:String(d._id), totalTests:Object.keys(t).length, sampleEntry:entry}));
  }
});
if(shown===0) print(JSON.stringify({_note:"no non-null abTests in newest 400 — try larger scan or different field"}));
