# KPI Management — Odoo 20 Community

Module ya kufafanua, kupima na kufuatilia **Key Performance Indicators (KPI)** na **Scorecards** ndani ya Odoo 20 Community.

## Vipengele

| Kipengele | Maelezo |
|---|---|
| **Categories** | Balanced Scorecard tayari: Financial, Customer, Internal Processes, Learning & Growth |
| **KPI za manual** | Matokeo yanaingizwa kwa mkono kwa kila kipindi |
| **KPI za automatic** | Zinahesabiwa kutoka model yoyote ya Odoo: Count / Sum / Average / Min / Max, au **Ratio (%)** |
| **Vipindi** | Daily, Weekly, Monthly, Quarterly, Yearly |
| **Target & status** | Higher/Lower is better, warning threshold, Achievement %, status 🟢 On Track / 🟡 At Risk / 🔴 Off Track, na trend |
| **Scheduler** | Cron ya kila siku inahesabu kipindi cha sasa na kilichopita |
| **Alerts** | Activity (To-Do) kwa responsible KPI ikiwa Off Track |
| **Wizard** | Kuhesabu historia ya vipindi vya nyuma (backfill) |
| **Scorecards** | Weighted scorecard kwa kila mtumiaji (weights = 100), achievement cap, rating, na **ripoti ya PDF** |
| **Dashboard** | Kanban kwa category yenye progress bars, pamoja na Graph & Pivot analysis |
| **Security** | Makundi mawili (User / Administrator) + multi-company |

## Usakinishaji

1. Clone repo hii ndani ya folder la custom addons:
   ```bash
   git clone <repo-url> /opt/odoo/custom-addons/odoo-kpi-management
   ```
2. Ongeza path kwenye `odoo.conf`:
   ```ini
   addons_path = /opt/odoo/odoo/addons,/opt/odoo/custom-addons/odoo-kpi-management
   ```
3. Restart Odoo → **Apps** → *Update Apps List* → tafuta **KPI Management** → *Activate*.

Au kwa command line:
```bash
./odoo-bin -c odoo.conf -d <database> -i kpi_management
```

Kuendesha tests:
```bash
./odoo-bin -c odoo.conf -d <test_db> -i kpi_management --test-enable --test-tags=/kpi_management --stop-after-init
```

## Matumizi kwa ufupi

1. **KPI → Configuration → Categories**: hakiki au ongeza categories.
2. **KPI → Performance → KPIs → New**:
   - Weka jina, code, target, direction (higher/lower is better) na frequency.
   - Tab ya *Computation*: chagua `Manual`, `Aggregate` au `Ratio`.
     - Mfano wa Aggregate: Model `Sales Order`, Date Field `Order Date`, Aggregation `Sum`, Value Field `Total`, Filter `state in (sale)`.
     - Mfano wa Ratio: Model `Lead/Opportunity`, Denominator = leads zote, Filter = `won`.
3. Bonyeza **Compute Current Period** au **Compute History** (wizard).
4. **Dashboard** inaonyesha hali ya KPI zote kwa rangi.
5. **Scorecards**: chagua mtumiaji, kipindi, ongeza KPI na weights (jumla 100) → *Start* → *Mark as Done* → Print PDF.

## Haki za upatikanaji

| Kundi | Uwezo |
|---|---|
| **KPI / User** | Anaona KPI anazohusika nazo (responsible, contributor, follower au ziko kwenye scorecard yake), matokeo yake, na scorecards zake. Anaweza kuingiza matokeo ya KPI anazozisimamia. |
| **KPI / Administrator** | Kila kitu: kusanidi KPI, categories, scorecards na kuhesabu. |

> Hesabu za automatic zinafanywa kwa `sudo()` ili KPI ionyeshe takwimu za kampuni nzima; kwa hiyo ni Administrator tu anayeweza kusanidi chanzo cha data.

## Muundo wa module

```
kpi_management/
├── __manifest__.py
├── models/        kpi_category, kpi_definition, kpi_value, kpi_scorecard
├── wizard/        kpi_compute_wizard
├── views/         dashboard, forms, lists, graph, pivot, menus
├── security/      kpi_security.xml, ir.access.csv  (muundo mpya wa Odoo 20)
├── data/          categories, scheduled action
├── demo/          KPI na scorecard za mfano
├── report/        Scorecard PDF
└── tests/
```

## Maelezo ya kiufundi (Odoo 20)

- Security inatumia `ir.access.csv` (Odoo 20 iliunganisha record rules na access rights kuwa `ir.access` yenye domain).
- Makundi yanatumia `res.groups.privilege` na `user_ids`.
- Views zinatumia `<list>`, `<chatter/>` na kanban `t-name="card"`.
- Constraints zinatumia `models.Constraint`.

Imejaribiwa kwenye Odoo 20.0 Community (Python 3.13, PostgreSQL 16): install na demo data, tests 8 zote zimepita, cron, wizard, report na access rights.

## Leseni

LGPL-3
