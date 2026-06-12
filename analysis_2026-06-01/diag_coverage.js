// Coverage check for the 3 analytics sub-types: docs, day range, distinct versions.
// Run: mongosh "$PS_MONGO_URI" --quiet diag_coverage.js > diag_coverage.jsonl
["analyticsPage","analyticsKpi","analyticsResponse"].forEach(function(t){
  try{
    var r=db.analytics.aggregate([
      {$match:{type:t}},
      {$facet:{
        s:[{$group:{_id:null,docs:{$sum:1},minDay:{$min:"$day"},maxDay:{$max:"$day"}}}],
        v:[{$group:{_id:"$campaignVersionId"}},{$count:"n"}],
        c:[{$group:{_id:"$campaignId"}},{$count:"n"}]
      }}
    ],{allowDiskUse:true}).toArray()[0];
    print(JSON.stringify({
      type:t,
      docs: r.s[0] ? r.s[0].docs : 0,
      minDay: r.s[0] ? String(r.s[0].minDay) : null,
      maxDay: r.s[0] ? String(r.s[0].maxDay) : null,
      distinctVersions: r.v[0] ? r.v[0].n : 0,
      distinctCampaigns: r.c[0] ? r.c[0].n : 0
    }));
  }catch(e){ print(JSON.stringify({type:t,_err:String(e).slice(0,150)})); }
});
