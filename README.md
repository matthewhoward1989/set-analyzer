# The Set Analyzer (offline static site)

Open `index.html` in any browser. It works with no server and no internet connection, because all data is loaded from `data/all.js`.

Pages: `index.html` (home + global search) · `sets.html` · `set.html?id=<set id>` (checklist, Top 5, team breakdown, parallels, comps, sources, gaps) · `teams.html?t=<LEAGUE>|<Team>` · `players.html?p=<Player>`.

## Data layout
- `sets/<id>.json`: one normalized file per release:
  `{id,name,sport,league,release,cards:[{card_no,player,team,set,rc,auto,country,first_bowman?}],parallels:[{print_run,parallel,odds,applies_to?,formats?}],comps:[{card_no,player,set?,card,price,net_est,as_of,basis,sales_30d,source,url}],boxes:[],case_hits:{names:[],source_text,source,status:"published"|"unknown"},sources:[{name,url,fetched,note}],gaps:[]}`
- `build_site.py`: merges every `sets/*.json` into `data/all.js`. It normalizes teams (league + current franchise, e.g. Oakland Raiders → Las Vegas Raiders; college/HS → "NCAA/Other") and flags `case_hit` when a card's subset name contains a published case-hit name.
- `extract_cardsmiths.py`: turns a saved Cardsmiths Breaks `/full-checklist/` page into a set file.

## Add a set
1. Save the checklist page: `curl -sL -A "Mozilla/5.0" -o ../raw/cs_<slug>.html https://cardsmithsbreaks.com/full-checklist/<slug>/`
2. `python3 extract_cardsmiths.py <id> "<Set name>" <Sport> <NFL|NBA|NHL|MLB> ../raw/cs_<slug>.html <url>`
   (For another source, write any script that outputs the same JSON shape.)
3. Check `sets/<id>.json`. Add comps only from real, dated sold data with source URLs. Add case hits only if a source publishes them (otherwise leave `status:"unknown"`). Add notes to `gaps`.
4. If needed, add team aliases or relocations to `ALIAS` in `build_site.py`.
5. `python3 build_site.py`, then open `index.html`.

## Rules
Use real, cited numbers only. Mark anything missing as a gap. Net, sports and non-sport sets (eBay) = sale − 13.25% − $0.40 − supplies (~$1 raw / ~$3 graded, estimate). Net, Pokémon/TCG sets (TCGplayer Level 1-4 Marketplace seller) = market − min(10.75% × market, $75 per product) − (2.5% × market + $0.30), before shipping and sales tax; source: TCGplayer Help Center "TCGplayer Fees" (https://help.tcgplayer.com/hc/en-us/articles/201357836-TCGplayer-Fees). Implemented as `tcgNet()` in app.js and in extract_pokemon.py. This is market data, not buying advice.

## Breakers section
- `breakers.html` (desk with overview + per-set panel) and the **Breaker panel** tab on `set.html?id=<id>&tab=breaker`, rendered by `breaker.js`.
- Data: `breakers/<set id>.json` holds `boxes` (from `extract_boxes.py <id> ../raw/<cardsmiths page>`), `market` (HobbyMonitor MSRP, box/case asks and team spots as published, recorded in `add_breaker_market.py` with url/as_of/sample n), `checked` sources, and `gaps`. `build_site.py` attaches it to each set.
- The model estimate (share = weighted team share of autos/case hits/RC/prospects × case cost) is shown with its formula and always labeled MODEL. The case-cost vs. sum-of-spots margin is only shown when every team in one format has a real price (not the case yet).

## SSP (replaces case hits as the main metric)
SSP = published hobby pack odds imply < 1 per hobby case (`odds_packs > packs_per_box × boxes_per_case`). Odds are stored in `sets/<id>.json` under `odds` (`rows: [{subset, parallel, per_unit:[per hobby case, other formats...]}]`):
- `odds_extract.py <id> ../raw/ckd_<x>.json <url>`: Cardsmiths checklist data (`/wp-json/csb/v1/ckd/<id>` linked from the checklist page; run rates come from manufacturer odds).
- `prose_odds.py <id> <raw page>`: fills any missing subset-level odds from Cardsmiths' "About one per X cases in Hobby" lines.
- Hand-entered odds (e.g. O-Pee-Chee Platinum from Checklist Insider) use the same row shape with a `published` text field.
`build_site.py` (`apply_ssp`) tags cards `ssp`, `x_cases`, `pack_odds`, `odds` = published / not in hobby / unknown. The old case-hit list survives only as `named_case_hit`.

## Checklist Insider sets (hockey)
`python3 extract_checklistinsider.py <id> "<Set name>" Hockey NHL ../raw/ci_<slug>.html https://www.checklistinsider.com/<slug>` parses each "<Subset> Checklist" section (card lines, "Pack odds/Odds -" lines, "Parallels:" lines) plus the product configuration. It writes `sets/<id>.json` (with hobby odds → per-case rates) and `breakers/<id>.json` (box config). If curl gets a bot check, save the page with headless Chrome `--dump-dom`.

## Pokémon TCG sets
`python3 extract_pokemon.py` builds `sets/ptcg-*.json` and `breakers/ptcg-*.json` from TCGdex card JSON in `../raw/tcgdex/` plus the cited TCGplayer community pull rates (n stated) and sealed MSRP/market prices hard-coded at the top of the script. Pokémon -> `player`, type -> `team`, rarity -> `set`; `kind:"tcg"`. Tier basis = specific-card rate (rarity rate ÷ cards in rarity) × packs per case; sets without a booster box/case get per-ETB odds and no tier.

## Non-sport sets (Marvel, Star Wars)
Same Cardsmiths pipeline; the checklist has no team column, so `team` is "—" and the set is marked `kind:"nonsport"` (subset view instead of team view, character Top 5, excluded from Breakers/team pages).


## Breakers team-price model v2 (2026-10-22)
breaker_model.py (run by build_site.py). price(team) = case cost x K x [A x chase-value share + (1-A) x checklist share].
Chase-value share uses chase_prices.json net values scaled by print run (min(N,100)/100). K = sum of all spots / case cost on full-case lists;
A fitted on full-case lists in breakers/observed.json (public breaker PYT price lists, cited + dated). Dollar figures are shown only for sets
that have observed team prices to check against; others say "not enough data". eval_model.py prints old vs new error per observed point.

## Sold spot prices
breakers/sold/<set_id>.json holds eBay SOLD team-spot data (headline on the Breakers page). Add more with `python3 ingest_sold_spots.py input.json` (format in the script docstring), then `python3 build_site.py`.

## extract_upperdeck.py — Upper Deck official checklist extractor

Builds `sets/<id>.json` and `breakers/<id>.json` from a saved upperdeck.com/checklist/<slug>/ page.

```
python3 extract_upperdeck.py <id> "<name>" "<release>" <raw_html> <checklist_url> \
    <packs_per_box> <cards_per_pack> <boxes_per_case> "<box config source>" <box config url>
```

- Non-parallel rows become cards; rows labelled "parallel" / "printing plates" go to the parallel ladder.
- Columns: player = "Description" (falls back to "Player Name"); odds = "Stated Odds" (falls back to "Odds").
- Hobby odds `a:b h`, `a:b Hobby` or a bare `a:b` → per-case rate = (a/b) × packs per case. No hobby odds → "odds unknown" (never invented).
- Multi-team cards ("New York/New York" + "Islanders/Rangers") are split into one row per team (`multi_team`, `players` fields); duplicates removed.
- Box config is credited via the source/url arguments. Fetch pages slowly with a browser UA (upperdeck.com returns 403 when rate-limited).
