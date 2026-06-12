"""Map discovered TF-IDF clusters -> human vertical taxonomy, write per-funnel labels."""
import pandas as pd
from pathlib import Path
D = Path(__file__).parent

# cluster -> (coarse_vertical, fine_label) based on top_terms + example inspection
M = {
 13:("Services / Consultation","Appointment & consultation lead-gen"),
 25:("Real Estate","Real estate / home (EN)"),
 30:("Recruiting","General job applications"),
 7 :("Recruiting","Jobs — benefits/comp focused"),
 23:("Subscription / Membership","Membership FAQ / cancellation"),
 16:("Recruiting","Apprenticeship / Ausbildung"),
 1 :("Recruiting","Apprenticeship quiz"),
 31:("Recruiting","Application submit"),
 35:("Solar / Energy","Solar PV quote (DE)"),
 22:("Recruiting","Application / matching"),
 6 :("Business / Agency","AI/agency/marketing growth (EN)"),
 27:("Education / Training","Weiterbildung / Bildungsgutschein"),
 5 :("Other-language","Dutch (NL) — vertical TBD"),
 17:("Online Course / Coaching","Make-money / business course (DE)"),
 37:("Recruiting","Healthcare & care staff (Pflege/Erzieher)"),
 34:("Real Estate","Property listings / Expose (DE)"),
 11:("Recruiting","Application / matching"),
 33:("Legal / Benefits","US disability benefits (EN)"),
 20:("Recruiting","Jobs Switzerland (EFZ/AG)"),
 4 :("Recruiting","Fast-apply full-time"),
 32:("Real Estate","Property valuation / seller (DE)"),
 19:("Recruiting","Dental practice staff (ZFA)"),
 24:("Beauty / Aesthetics","Skincare / aesthetics (DE)"),
 38:("Other-language","Romance langs (ES/IT/RO) — TBD"),
 0 :("Other-language","French (FR) — vertical TBD"),
 12:("Recruiting","Application + consent-heavy"),
 28:("Health / Home services","Dental & garden rooms (EN/UK)"),
 14:("Recruiting","Truck drivers (LKW/CE)"),
 29:("Recruiting","Automotive technicians (KFZ)"),
 36:("Noise / Compliance","Facebook TM disclaimer"),
 18:("Solar / Energy","Solar / home energy (EN)"),
 21:("Education / Training","Tutoring & trading courses"),
 15:("Noise / Compliance","Privacy/consent boilerplate"),
 39:("Financial Services","Bausparkasse / kids savings (DE)"),
 3 :("Recruiting","Application / intro call"),
 10:("Recruiting","Application / matching"),
 26:("Recruiting","Job offer quiz"),
 2 :("Recruiting","Electrician (Elektro)"),
 8 :("Recruiting","Application via WhatsApp"),
 9 :("Food / E-commerce","Turkish food (börek)"),
}

cl = pd.read_csv(D/"data/funnel_clusters.csv")
cl["vertical"]   = cl.cluster.map(lambda c: M.get(c,("Unknown","?"))[0])
cl["fine_label"] = cl.cluster.map(lambda c: M.get(c,("Unknown","?"))[1])
cl.to_csv(D/"data/funnel_vertical.csv", index=False)

# landscape summary by coarse vertical, enriched with cvr/visitors
content = pd.read_csv(D/"data/funnel_content.csv", usecols=["campaignVersionId","visitors","cvr"])
j = cl.merge(content, on="campaignVersionId", how="left")
g = (j.groupby("vertical")
       .agg(n_funnels=("campaignVersionId","count"),
            total_visitors=("visitors","sum"),
            median_cvr_pct=("cvr", lambda s: round(100*s.median(),2)))
       .sort_values("total_visitors", ascending=False))
g["pct_funnels"] = (100*g.n_funnels/g.n_funnels.sum()).round(1)
g.to_csv(D/"data/vertical_summary.csv")
pd.set_option("display.width",200)
print(g.to_string())
