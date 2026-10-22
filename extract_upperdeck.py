"""Upper Deck official checklist page (upperdeck.com/checklist/<slug>/) -> sets/<id>.json + breakers/<id>.json box config.
Usage: python3 extract_upperdeck.py <id> "<Set name>" "<release>" <raw_html> <url> <packs_per_box> <cards_per_pack> <boxes_per_case> "<config source name>" <config url>
Cards = every non-parallel row (base, variations, inserts, autos). Parallel rows -> parallel ladder + odds rows.
Hobby odds 'a:b h|Hobby' -> a/b per pack -> per case = a/b * packs_per_case (subset-level rate, same convention as other sets). 'Random Inserts' = odds unknown."""
import sys,json,re,datetime,collections
from bs4 import BeautifulSoup as B
sid,name,rel,raw,url,ppb,cpp,bpc,cfgname,cfgurl=sys.argv[1:11];ppb,cpp,bpc=int(ppb),int(cpp),int(bpc);ppc=ppb*bpc
s=B(open(raw).read(),'lxml');rows=[[c.get_text(' ',strip=True) for c in r.find_all(['td','th'])] for r in s.find_all('tr')]
h=rows[0];ix={k:i for i,k in enumerate(h)}
oi=ix.get('Stated Odds',ix.get('Odds'));nd=next(i for k,i in ix.items() if '#' in k)
def g(r,k):
    if k=='Description' and k not in ix: k='Player Name'
    i=ix.get(k);return r[i] if i is not None and i<len(r) else ''
def hobby(od):
    m=re.search(r'([\d,]+)\s*:\s*([\d,]+)\s*(?:h\b|hobby)',od,re.I)
    if not m: m=re.match(r'^\s*([\d,]+)\s*:\s*([\d,]+)\s*$',od)  # bare ratio = single-format (hobby) product, e.g. Ice
    if not m: return None
    a,b=(float(x.replace(',','')) for x in m.groups());return a/b*ppc
cards=[];par=collections.OrderedDict();odds={}
for r in rows[1:]:
    if len(r)<=oi or r[0]=='Set Name': continue
    sub,od=r[0],r[oi]
    if 'parallel' in sub.lower() or 'printing plates' in sub.lower():
        par.setdefault(sub,dict(print_run=r[nd] or '—',parallel=sub,odds=od));
    else:
        cities=[x.strip() for x in g(r,'Team City').split('/')];names=[x.strip() for x in g(r,'Team Name').split('/')]
        if len(cities)!=len(names): cities=(cities*len(names))[:len(names)] if len(cities)==1 else cities[:len(names)]+['']*(len(names)-len(cities))
        teams=[]
        for ci,na in zip(cities,names):
            tm=re.sub(r'\s+',' ',(ci+' '+na).strip())
            if tm and tm not in teams: teams.append(tm)
        if not teams: teams=['—']
        players=[x.strip() for x in g(r,'Description').split('/')]
        for tm in teams:  # multi-team cards: one row per team so team pages/counts credit every club; flagged multi_team
            cards.append(dict(card_no=g(r,'Card'),player=g(r,'Description'),team=tm,set=sub,
              rc=bool(g(r,'Rookie')) or 'Young Guns' in sub or 'Rookie' in sub,auto=bool(g(r,'Auto')) or bool(re.search(r'auto|signature',sub,re.I)),country='',
              young_guns='Young Guns' in sub,print_run=r[nd],**({'multi_team':teams,'players':players} if len(teams)>1 else {})))
    if sub not in odds:
        v=hobby(od);odds[sub]=dict(subset=sub,parallel='base',per_unit=[round(v,5) if v else None],published=od or 'not stated')
odds_rows=list(odds.values())
src=dict(name='Upper Deck official checklist (card list + Upper Deck stated odds)',url=url,fetched=str(datetime.date.today()))
json.dump(dict(id=sid,name=name,sport='Hockey',league='NHL',release=rel,cards=cards,parallels=list(par.values()),comps=[],boxes=[],
  case_hits=dict(names=[],source_text='',source='',status='unknown'),sources=[src,dict(name=cfgname+' (hobby box configuration from the Upper Deck sell sheet)',url=cfgurl,fetched=str(datetime.date.today()))],
  odds=dict(formats=['Hobby'],boxes_per_unit=[bpc],units=['case'],rows=odds_rows,subset_alias={},status='published',source=src),
  gaps=['Subsets listed as "Random Inserts" on the Upper Deck checklist have no stated odds and are marked odds unknown.',
        'Parallels are listed in the parallel ladder, not as separate checklist rows.','No case-hit list is published, so named case hits are unknown.']),open(f'sets/{sid}.json','w'),indent=1)
bp=f'breakers/{sid}.json'
try: b=json.load(open(bp))
except Exception: b=dict(market=[],market_source='',checked=[],gaps=[])
b['boxes']=[{'format':'Hobby','Packs × cards':f'{ppb} × {cpp}','Cards per box':str(ppb*cpp),'Boxes per case':str(bpc),'lowest_ask':''}]
b['box_source']=dict(name=cfgname,url=cfgurl,fetched=str(datetime.date.today()))
json.dump(b,open(bp,'w'),indent=1)
print(sid,len(cards),'cards',len(par),'parallels',sum(1 for r in odds_rows if r['per_unit'][0]),'/',len(odds_rows),'subsets with hobby odds','Flyers:',sum('Flyers' in c['team'] for c in cards))
