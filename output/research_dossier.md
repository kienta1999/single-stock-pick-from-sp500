# Research Dossier — Stock-Pick Funnel
Generated: 2026-06-21 · Shortlist source: `output/shortlist.json` (2026-06-21 22:34)

14 shortage-thesis candidates, deep-researched by 4 parallel Opus subagents. Scores
are 0–10 (shortage = how supply-constrained the demand is; irreplaceability = how
impossible it is for a customer/hyperscaler to in-source or a substitute to bypass).

## Score table

| Ticker | Sector / sub-industry | Shortage | Irreplaceability | Headline demand/backlog signal |
|--------|----------------------|:--------:|:---------------:|--------------------------------|
| NVDA | Semiconductors | 9 | **9** | Supply commitments ~$95.2B (≈2x QoQ), locked through CY2027 |
| MU | Semiconductors | **9** | 7 | HBM **sold out through 2026**; customers get 50–67% of demand; FY rev +196% |
| GE | Aerospace & Defense | 9 | **9** | **$211.3B** backlog (Q1'26); "demand exceeds supply" |
| HWM | Aerospace & Defense | 9 | **9** | Engine Products +29%; record customer backlogs; single-crystal blade choke-point |
| AVGO | Semiconductors | 8 | 7 | AI rev +143%; FY AI guide $56B; >$100B AI target FY27; $6B new orders |
| SNDK | Tech HW/Storage | 8 | 4 | NAND cost +up-to-234%; guided next-qtr rev to $8B; shortage to 2028 |
| LLY | Pharmaceuticals | 8 | 7 | GLP-1 demand >> supply; rev +56%; FY guide $82–85B |
| LRCX | Semicap Equip | 8 | 8 | WFE>$140B; adv-packaging +50%+; visibility to 2028 fabs |
| CAT | Constr/Heavy Machinery | 8 | 6 | **$63B** record backlog (+79% YoY); datacenter power-gen +48% |
| KLAC | Semicap Equip | 9 | **9** | ~58% process-control share; toll-booth on every leading-edge wafer |
| APH | Electronic Components | 7 | 7 | Record **$9.4B** orders (+78%); book-to-bill 1.24 |
| CDNS | Application Software | 7 | 8 | Record **$8.0B** backlog; EDA duopoly |
| AMAT | Semicap Equip | 7 | 7 | Equip rev guide >30% CY26; ~$15B backlog; visibility to 2028 |
| NEM | Gold | 4 | 2 | Record $4,900/oz realized; but commodity price-taker, 2026 output trough |

---

## Batch 1 — Memory & AI compute

### MU — Micron · shortage 9 / irreplaceability 7
- **Shortage:** FY Q2'26 (Mar 18 2026) — **sold out of HBM through 2026**; customers receiving only 50–67% of demanded HBM. DRAM rev +74% QoQ on mid-60% ASP gains; NAND +82% QoQ on high-70% ASP. New capacity (Idaho, Tongluo) adds no wafers until H2 2027 → 2026 supply fixed.
- **Backlog:** No single $ figure; "sold out through 2026," LTAs into 2027. FY rev +196%. FQ3 guide $18.7B / $8.42 EPS / ~68% GM. Hard $-backlog: not found.
- **Position:** #3 in HBM (SK hynix 62%, **MU 21%**, Samsung 17% — overtook Samsung). ~20% of Nvidia HBM4 allocation.
- **Irreplaceability:** Only **3 firms on earth** make HBM; HBM4 qual is a multi-quarter packaging/process hurdle; hyperscalers can't in-source memory. Capped at 7 because it's #3-of-3 and customers tri-source.
- **Catalysts:** Wave of June PT hikes (UBS $1,625, Raymond James $1,100, TD Cowen $1,500, RBC $1,200). FQ3 earnings **due June 24, 2026**. HBM4 samples at 11 Gbps.
- **Risks:** Memory cyclicality (Goldman cautious ~$400 PT); SK hynix leads HBM4; Samsung recovering; demand cooling after 2027.
- **Verdict:** Genuine sold-out supercycle with real pricing power, but #3-of-3 in a historically cyclical commodity = most "is-this-the-top" risk.

### NVDA — Nvidia · shortage 9 / irreplaceability 9
- **Shortage:** Q1 FY27 (qtr ended Apr 26 '26) record **$81.6B rev (+85%)**, Data Center $75.2B (+92%); Blackwell 300 ramp; sold-out posture.
- **Backlog:** **Supply purchase commitments ~doubled to $95.2B** (from $50.3B), locking capacity through CY2027 — cleanest quantified forward-demand proxy.
- **Position:** #1, ~70–80% of datacenter AI accelerators; AMD ~6–8%; custom silicon ~15–20%.
- **Irreplaceability (9, highest):** CUDA ecosystem lock-in — strongest moat in the group. Capped from 10 because hyperscaler ASICs (Google TPU >75% of Gemini; AWS Trainium >50% of Bedrock) growing ~44.6% vs ~16% merchant GPU in 2026, eroding the inference edge.
- **Catalysts:** Q1 FY27 blowout (late May); Vera Rubin next cycle; consensus PT ~$305–309.
- **Risks:** ~$5T valuation must keep beating; China overhang; structural custom-ASIC share shift.
- **Verdict:** Most irreplaceable + best-quantified demand, but at ~$5T the explosive multiple is harder to repeat and in-sourcing nibbles edges.

### AVGO — Broadcom · shortage 8 / irreplaceability 7
- **Shortage:** Q2 FY26 (Jun 3 '26) record **$22.2B rev (+48%)**; AI semi $10.8B (+143%). FY AI guide raised to **$56B (+180%)**; Q3 AI ~$16B; reiterated **>$100B AI rev FY27**.
- **Backlog:** Multi-GW deals w/ Google, Anthropic, OpenAI, Meta; **$6B new AI orders from 2 customers**; Apollo/Blackstone $35B financing. Single $-backlog: not found.
- **Position:** #1 custom AI ASIC (~70%+ share; Marvell #2 20–25%). Powers Google TPU, Meta MTIA, MSFT Maia.
- **Irreplaceability:** Deep SerDes/networking IP + multi-year co-design. Capped at 7 — its product *enables* customer in-sourcing of compute, and Google reportedly diversifying TPU suppliers (self-inflicted disintermediation).
- **Catalysts:** Q2 beat + raise; PT hikes (JPM $580, Jefferies $550); ~$522 consensus.
- **Risks:** Heavy AI dependence; customer concentration; Google diversification (~12.6% pullback noted).
- **Verdict:** "Picks-and-shovels of in-sourcing" leader with deepest hyperscaler contracts, but its moat shrinks each time it teaches a customer to route around the merchant GPU.

### SNDK — SanDisk · shortage 8 / irreplaceability 4
- **Shortage:** NAND shortage; eSSD displacing HDD. Latest qtr rev $3.03B (+61%), EPS $6.20; **guided next qtr to $8B rev / $31 EPS** (vs ~$6.49B consensus). Gartner: NAND cost +up-to-234% in 2026; shortage to 2028.
- **Backlog:** None disclosed; signal is the guidance jump.
- **Position:** **#5 NAND (~12%)** — Samsung #1 (~29–32%), then SK hynix, Kioxia. Co-develops BiCS NAND with Kioxia.
- **Irreplaceability (4, lowest):** Sub-scale #5 in a commodity co-developed with a partner; no replication barrier vs larger Korean rivals. Not in-sourcing risk, but easily substituted.
- **Catalysts:** June 8 PT hikes (Cantor $2,900, Mizuho $2,200, BofA $2,100); stock +4,000% since 2025 WDC spinoff, above $2,000.
- **Risks:** Most cyclical/momentum-driven; parabolic chart; eSSD durability uncertain; ~15% downside to consensus per some.
- **Verdict:** Most explosive price action + steepest guidance, but thinnest moat and highest round-trip risk.

## Batch 2 — Semicap equipment & EDA

Macro: 2026 WFE raised to **>$140B**, Street models **>$200B by 2027** (Barclays $209.5B); AMAT tracks **100+ active fab projects**; binding constraint is **cleanroom floor space**, not orders.

### LRCX — Lam Research · shortage 8 / irreplaceability 8
- Etch/depo intensity rising on GAA/HBM/adv-packaging; adv-packaging rev guided **+50%+ CY26**; visibility to fabs opening 2028. Record FQ3 rev **$5.84B (+24%)**, 4th straight beat. #1 etch (~45%), #2 depo (~17%). Morningstar wide moat. Citi PT $450, Barclays $335. Risk: China curbs hit ~$600M of 2026 rev; #2 in depo. **Verdict:** wide-moat etch leader fully levered to WFE wave; two credible rivals + China drag cap the "irreplaceable" case.

### KLAC — KLA · shortage 9 / irreplaceability 9 (highest moat in group)
- Process-control intensity rises faster than WFE; adv-packaging rev $635M→~$1B. Guides high-teens 2026 rev growth, process-control >20%. **Dominant #1 ~58% process control, >85% optical wafer inspection.** Q3 FY26 rev **$3.415B**, EPS $9.12 (beat); Q4 GM ~61.75% (best in group). Near-monopoly + certification lock-in; no one in-sources inspection. Risk: cyclical (least so of four), China, premium valuation. **Verdict:** toll-booth on every leading-edge wafer — best moat + margins short of ASML.

### AMAT — Applied Materials · shortage 7 / irreplaceability 7
- Broadest WFE; guides equip rev **>30% CY26**; 100+ fab projects; bookings to 2028. Backlog **$15.0B** (Oct'25 10-K; Q2 FY26 ~$15B approx/unconfirmed). Q2 FY26 record rev **$7.91B**, EPS $2.86 beat, GM ~50% (best in 25+ yrs). #1 overall WFE/deposition; #2 to KLA in inspection (losing share). Risk: most China-exposed (~$600M hit); FQ1 rev was -2% YoY. **Verdict:** broadest/cheapest WFE optionality, most cyclical + China-exposed, weakest single-segment moat.

### CDNS — Cadence · shortage 7 / irreplaceability 8
- Demand-surge (not hard shortage) for leading-edge design + AI verification compute. **Record backlog $8.0B** end-Q1'26; ~$4.0B RPO within 12mo — firmest disclosed order book of the four. EDA duopoly (SNPS ~31% / CDNS ~30% / Siemens ~13%). Q1'26 rev +19%, 45% op margin, raised FY to 17%, "Rule of 60." Foundry certification lock-in. Risk: priciest multiple; China policy football; Synopsys co-equal substitute. **Verdict:** highest-quality recurring compounder with clearest backlog + duopoly moat, but demand-surge story already richly valued.

## Batch 3 — Pharma & aerospace/industrial

### LLY — Eli Lilly · shortage 8 / irreplaceability 7
- GLP-1/incretin demand >> supply 2+ yrs; FDA shortage officially resolved but maintenance-dose gaps persist; ~$25B+ capacity buildout. Q1'26 rev **+56% to $19.8B**; Mounjaro +125%, Zepbound +79%. FY guide $82–85B. #1 branded GLP-1 (~60% vs Novo ~40%); tirzepatide efficacy leader. Moat: biologics manufacturing complexity + oral pipeline. **Substitution risk (real):** oral GLP-1 (own orforglipron — self-disruption) and semaglutide biosimilars (2031 global). Catalysts: Q1 beat ($8.55 vs $6.66) + raise; orforglipron Lancet superiority; oral pill launched. Risk: highest absolute valuation; substitution; drug-pricing politics. **Verdict:** category king of a still-undersupplied $100B market, now its own biggest disruptor — explosive but most genuine substitution risk.

### HWM — Howmet Aerospace · shortage 9 / irreplaceability 9
- Direct aero-parts shortage; OEMs chasing rate hikes on "record backlogs"; flight-critical single-crystal superalloy turbine blades are the engine-ramp bottleneck. Q1'26 rev +19% to $2.31B; Engine Products +29% to $1.25B; FY guide raised $9.58–9.73B. #2 castings (~12–15%) behind PCC; PCC+HWM+CPP ≈75% (oligopoly). **Irreplaceability 9:** single-crystal casting IP, ITAR + FAA qual (years/part), dual-sourcing flight-critical hardware costly/slow, decades-long aftermarket; OEMs can't in-source at scale. Catalyst: Q1 beat (EPS $1.22 vs $1.11, +42%) + raise. Risk: aero cyclicality, Mideast spares risk, customer concentration. **Verdict:** irreplaceable choke-point behind the jet-engine ramp — highest moat, cleanest shortage, lowest disintermediation risk.

### GE — GE Aerospace · shortage 9 / irreplaceability 9
- Explicit "demand exceeds supply" despite 25%+ rev growth 5 qtrs; LEAP deliveries 520 in Q1'26 vs 319; spare-parts delinquency +~70% since end-2024; >95% of spare-parts rev already in backlog. **Backlog $211.3B** (Q1'26 10-Q). Q1 rev +29% to $11.6B, EPS $1.86 (+25%). #1 — CFM powers ~72% of active narrowbody fleet; LEAP sole-source on 737 MAX, >55% A320neo; aftermarket ~70% of rev. Moat: engine IP, 25–30yr service tail, FAA maintenance-data exclusivity, CFM JV; Pratt GTF hampered by powder-metal issues. Risk: own supply constraints cap conversion; geopolitics; rich valuation; thesis is consensus. **Verdict:** near-monopoly on the dominant narrowbody engine with $211B backlog — highest-quality compounder, but much is already consensus.

### CAT — Caterpillar · shortage 8 / irreplaceability 6
- AI/datacenter power-gen shortage; Power & Energy to users +32%, datacenter power-gen +48%; tripling large recip-engine capacity to ~3x 2024. **Record $63B backlog (+79% YoY)**. Q1'26 rev $17.4B (+22%), EPS $5.54 (+30%). #1 construction/mining; Solar Turbines leader in industrial gas turbines. **Irreplaceability 6 (weakest of batch):** power-gen substitutable (Cummins, GE Vernova, fuel cells, grid, batteries); engines not certification-locked; multi-source. Catalyst: Q1 beat + raise; MSFT–Nvidia infra win; MS PT $915, JPM $1,125. Risk: most cyclical; ~44x P/E; PT ~$890 ≈ price (priced in); tariffs $2.2–2.4B. **Verdict:** genuine AI-power beneficiary with $63B backlog, but most cyclical, most replaceable, most fully-valued of its batch.

## Batch 4 — Connectors & gold

### APH — Amphenol · shortage 7 / irreplaceability 7
- AI-datacenter interconnect; Q1'26 IT datacom +99% USD/+81% organic, ~41% of sales; "virtually all" sequential growth AI-related. **Record orders $9.4B (+78%), book-to-bill 1.24.** Q1 rev $7.6B (+58%), EPS $1.06 (+68%, beat). Co-leader/emerging #1 (TE ~14.8% #2 close); CommScope CCS $10.5B deal closed Jan'26 (~+17% rev). Moat: engineered, designed-in, high switching cost — but fragmented/competitive, NO long-term agreements (re-win each gen). Risk: cyclicality, hyperscaler capex swing, CCS integration, valuation. **Verdict:** high-quality picks-and-shovels AI-interconnect leader, but competitive/cyclical components business, not a hard monopoly.

### NEM — Newmont · shortage 4 / irreplaceability 2
- Demand-pull, not structural shortage. Realized **$4,900/oz Q1'26** (vs $2,944 yr ago). Reserves 118.2M oz (#1). But 2026 output guided **down** to ~5.26M oz (trough) from 5.9M; Q1 ~60koz Boddington bushfire shortfall. AISC 2026 ~$1,680/oz. #1 producer (~15% top-tier share). **Irreplaceability 2:** gold is fungible, Newmont a price-taker, no pricing power; ETFs/bullion route around miners entirely. Catalyst: record FCF $3.1B, **$6B buyback**, broad PT hikes (mean ~$141 vs ~$120). Risk: entire thesis is the gold price; output declining, AISC rising. **Verdict:** dominant lowest-cost gold major riding record prices, but a commodity price-taker with a substitutable product — explosive upside depends on gold, not a structural shortage.
