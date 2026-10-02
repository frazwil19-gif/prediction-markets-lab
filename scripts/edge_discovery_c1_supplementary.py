"""Edge discovery cycle 1 -- SUPPLEMENTARY (run after the main script; motivated by ATLAS X1 favourite-longshot finding,
disclosed as a follow-up, not pre-listed): (A) de-vig method comparison on 16 xgabora leagues (B365 close);
(B) probability-source comparison on football-data per-book E0/E1/SC0 (median UK/all books, Pinnacle; proportional vs power).
Usage: python scripts/edge_discovery_c1_supplementary.py <xgabora Matches.csv> <processed/football dir>
"""
import sys
XG, FD = sys.argv[1], sys.argv[2].rstrip("/") + "/"
import numpy as np, pandas as pd
from scipy.optimize import brentq

def prop(inv): return inv/inv.sum(1,keepdims=True)
def power(inv):
    out=np.empty_like(inv)
    for i,r in enumerate(inv):
        k=brentq(lambda k:(r**k).sum()-1,0.5,3); out[i]=r**k
    return out
def shin(inv):
    out=np.empty_like(inv)
    for i,r in enumerate(inv):
        B=r.sum()
        def f(z):
            p=(np.sqrt(z*z+4*(1-z)*r*r/B)-z)/(2*(1-z)); return p.sum()-1
        try: z=brentq(f,0,0.4)
        except ValueError: z=0
        out[i]=(np.sqrt(z*z+4*(1-z)*r*r/B)-z)/(2*(1-z))
    return out
d=pd.read_csv(XG,low_memory=False,usecols=['Division','MatchDate','FTResult','OddHome','OddDraw','OddAway'])
d['date']=pd.to_datetime(d.MatchDate)
lg=["E0","E1","SC0","N1","D1","F1","SP1","I1","P1","B1","E2","E3","SP2","D2","I2","F2"]
d=d[d.Division.isin(lg)&(d.date>='2020-07-01')&(d.date<'2026-07-01')&(d.OddHome>1)&(d.OddDraw>1)&(d.OddAway>1)].copy()
d['season']=np.where(d.date.dt.month>=7,d.date.dt.year,d.date.dt.year-1)
inv=1/d[['OddHome','OddDraw','OddAway']].to_numpy()
d=d[d.FTResult.isin(['H','D','A'])].copy(); inv=1/d[['OddHome','OddDraw','OddAway']].to_numpy(); y=d.FTResult.map({'H':0,'D':1,'A':2}).astype(int).to_numpy()
rng=np.random.default_rng(1)
P={'proportional':prop(inv),'power':power(inv),'shin':shin(inv)}
for per,mask in (('discovery',d.season<=2022),('confirmation',d.season>=2023)):
    mask=mask.to_numpy()
    base=-np.log(P['proportional'][mask][np.arange(mask.sum()),y[mask]])
    for k,p in P.items():
        pm=p[mask]; ll=-np.log(pm[np.arange(len(pm)),y[mask]])
        diff=ll-base; b=diff[rng.integers(0,len(diff),(2000,len(diff)))].mean(1)
        fav=pm.max(1); fw=(pm.argmax(1)==y[mask])
        hp=fav>=0.7; lo=pm<0.2; 
        lowp=pm[lo]; lowwon=(np.eye(3)[y[mask]][lo])
        print(per,k,'LL',round(ll.mean(),5),'d',round(diff.mean(),5),np.round(np.percentile(b,[2.5,97.5]),5),'fav>=.7 n',hp.sum(),'pred',round(fav[hp].mean(),4),'act',round(fw[hp].mean(),4),'longshot<.2 pred',round(lowp.mean(),4),'act',round(lowwon.mean(),4))



U=FD
b=pd.concat([pd.read_csv(U+'cycle_001_bookmaker_markets_full.csv'),pd.read_csv(U+'h_fb2_002_sealed_oos_2025_26_bookmaker_markets.csv')])
m=pd.concat([pd.read_csv(U+f,usecols=['match_id','season','full_time_result']) for f in ('cycle_001_matches_full.csv','h_fb2_002_sealed_oos_2025_26_matches.csv')]).drop_duplicates('match_id')
b=b[(b.home_odds>1)&(b.draw_odds>1)&(b.away_odds>1)]
inv=1/b[['home_odds','draw_odds','away_odds']].to_numpy()
def power(r):
    k=brentq(lambda k:(r**k).sum()-1,0.3,3); return r**k
pw=np.array([power(r) for r in inv]); pr=inv/inv.sum(1,keepdims=True)
b[['pwH','pwD','pwA']]=pw; b[['prH','prD','prA']]=pr
rng=np.random.default_rng(2)
for snap in ('opening','closing'):
    x=b[b.price_timing==snap]
    srcs={}
    srcs['median_all_prop']=x.groupby('match_id')[['prH','prD','prA']].median()
    srcs['median_all_power']=x.groupby('match_id')[['pwH','pwD','pwA']].median()
    uk=x[x.bookmaker.isin(['B365','WH','BW','BF','1XB'])]
    srcs['median_UK_prop (production-like)']=uk.groupby('match_id')[['prH','prD','prA']].median()
    srcs['median_UK_power']=uk.groupby('match_id')[['pwH','pwD','pwA']].median()
    ps=x[x.bookmaker=='PS'].set_index('match_id')
    srcs['PS_prop']=ps[['prH','prD','prA']]; srcs['PS_power']=ps[['pwH','pwD','pwA']]
    common=set.intersection(*[set(v.index) for v in srcs.values()])
    common=sorted(common)
    mm=m.set_index('match_id').loc[common]
    y=mm.full_time_result.map({'H':0,'D':1,'A':2}).to_numpy().astype(int)
    per=np.where(mm.season.isin(['2020_21','2021_22','2022_23']),'disc','conf')
    base=None
    for k,v in srcs.items():
        p=v.loc[common].to_numpy(); p=p/p.sum(1,keepdims=True)
        ll=-np.log(p[np.arange(len(y)),y])
        if base is None: base=ll
        out=[]
        for pp in ('disc','conf'):
            mk=per==pp; d=ll[mk]-base[mk]; bb=d[rng.integers(0,mk.sum(),(2000,mk.sum()))].mean(1)
            fav=p[mk].max(1); fw=p[mk].argmax(1)==y[mk]; hp=fav>=0.7
            out.append(f"{pp}: LL {ll[mk].mean():.5f} d {d.mean():+.5f} [{np.percentile(bb,2.5):+.5f},{np.percentile(bb,97.5):+.5f}] fav>=.7 {hp.sum()} {fav[hp].mean():.3f}->{fw[hp].mean():.3f}")
        print(snap,k,len(common),' | '.join(out))
