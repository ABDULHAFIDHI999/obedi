# Contact Football Team — Odoo 20 Community

Inaongeza chaguo la **Football Team** kwenye kila contact (res.partner) ya Odoo.

## Vipengele
- Model mpya `football.team` (jina, short name, nchi, ligi, uwanja, mwaka ilipoanzishwa, logo, website)
- Sehemu ya **Football Team** kwenye fomu ya contact (chini ya *Tags*)
- Column ya hiari kwenye list ya contacts, filter *Has Football Team* na *Group By Football Team*
- Smart button **Supporters** kwenye kila timu
- Timu za mwanzo: Simba SC, Yanga, Azam FC, Real Madrid, Barcelona, Man United, Arsenal, Chelsea, Liverpool
- Menu: **Contacts → Configuration → Football Teams**

## Usakinishaji (EasyInstance / server yoyote)
1. Ongeza repo hii kama custom addons repository (folder la `contact_football_team` liwe ndani ya addons path).
2. Restart Odoo, washa *Developer Mode*.
3. **Apps → Update Apps List** → tafuta **Contact Football Team** → *Activate*.

Command line:
```bash
./odoo-bin -c odoo.conf -d <database> -i contact_football_team
```

Tests:
```bash
./odoo-bin -c odoo.conf -d <database> -i contact_football_team --test-tags /contact_football_team --stop-after-init
```
