#!/usr/bin/env python3
"""Power-matched PCS reference LCI audit for the BESS manuscript.

Evidence: DNV (2024) model EH-0200-HA-M mass, composition and greenhouse-gas
coefficients; Sineng manufacturer data sheet; ENA device register.
Outputs are reference-process arithmetic, NOT a verified station-wide GWP100.
No network, solver, unseen source file or electricity data are required.
"""
from __future__ import annotations
import csv
import json
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

OUT = Path(__file__).resolve().parent
D = Decimal

# Published, rounded DNV component quantities (kg) and impact entries (kgCO2e).
material_rows = [
    ('aluminium', D('41'), D('599')),
    ('copper', D('16'), D('93')),
    ('steel', D('8'), D('21')),
    ('polypropylene', D('8'), D('34')),
    ('polycarbonate', D('2'), D('13')),
    ('iron', D('8'), D('21')),
    ('electronics', D('16'), D('393')),
]
assert sum((r[2] for r in material_rows), D('0')) == D('1174')
assert sum((r[1] for r in material_rows), D('0')) == D('99')
assert D('99') != D('98')  # rounded mass itemization exceeds declared mass by 1 kg

# DNV Table 3 and relevant transport text; per individual reference PCS.
GHG_MATERIAL = D('1174')
GHG_MANUFACTURE = D('65')
GHG_TRANSPORT = D('17.2')
PER_DEVICE_GHG = GHG_MATERIAL + GHG_MANUFACTURE + GHG_TRANSPORT

NAMEPLATE_KVA_45C = D('200')
PCS_MASS_KG = D('98')
PARALLEL_MAX_SINGLE_GROUP = 40
TARGET_KW = D('10000')

# Previously published stage-based EPD cross-product arithmetic in uploaded manuscript.
BYD_NONUSE_T = D('2275.28')
TRANSFORMER_8_NONUSE_T = D('153.26')
TRANSFORMER_9_NONUSE_T = D('172.42')

def ceil_decimal(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_CEILING))

def scenario(pf: str, transformer_count: int, transf_gwp_t: Decimal):
    power_factor = D(pf)
    n = ceil_decimal(TARGET_KW/(NAMEPLATE_KVA_45C*power_factor))
    return {
        'case': f'PF {pf}',
        'power_factor': pf,
        'pcs_model': 'EH-0200-HA-M',
        'count_PCS': n,
        'PCS_per_device_kVA_45C': str(NAMEPLATE_KVA_45C),
        'total_nominal_MVA': str(D(n)*NAMEPLATE_KVA_45C/D('1000')),
        'nominal_active_MW': str(D(n)*NAMEPLATE_KVA_45C*power_factor/D('1000')),
        'PCS_mass_t': str(D(n)*PCS_MASS_KG/D('1000')),
        'PCS_material_t_CO2e': str(D(n)*GHG_MATERIAL/D('1000')),
        'PCS_manufacturing_energy_t_CO2e': str(D(n)*GHG_MANUFACTURE/D('1000')),
        'PCS_transport_t_CO2e': str(D(n)*GHG_TRANSPORT/D('1000')),
        'PCS_candidate_total_t_CO2e': str(D(n)*PER_DEVICE_GHG/D('1000')),
        'minimum_AC_parallel_groups': ceil_decimal(D(n)/D(PARALLEL_MAX_SINGLE_GROUP)),
        'reference_transformer_count': transformer_count,
        'transformer_cross_EPD_t_CO2e': str(transf_gwp_t),
        'BYD_module_nonuse_t_CO2e': str(BYD_NONUSE_T),
        'cross_product_partial_total_t_CO2e': str(BYD_NONUSE_T+transf_gwp_t+D(n)*PER_DEVICE_GHG/D('1000')),
        'evidence_class': 'nonharmonized source-based candidate scenario; not station GWP100',
    }

records = [scenario('1.0',8,TRANSFORMER_8_NONUSE_T), scenario('0.9',9,TRANSFORMER_9_NONUSE_T)]
assert records[0]['count_PCS']==50 and records[1]['count_PCS']==56
assert D(records[0]['PCS_candidate_total_t_CO2e'])==D('62.81')
assert D(records[1]['PCS_candidate_total_t_CO2e'])==D('70.3472')
assert D(records[0]['cross_product_partial_total_t_CO2e'])==D('2491.35')
assert D(records[1]['cross_product_partial_total_t_CO2e'])==D('2518.0472')

with (OUT/'V72_PCS_process_ledger.csv').open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(records[0]))
    wr.writeheader();wr.writerows(records)

sources=[
    ('DNV 2024','Consulting LCA report, model and rounded kgCO2e process inventory; not an EPD','https://planning.sholland.gov.uk/OcellaWeb/viewDocument?file=dv_pl_files%5CH16-0596-24%5CBattery+Box+Life+Cycle+Assessment+%28Grange+Box%29+-+DNV+Report+Feb+2024+V3.pdf&module=pl', 'Report 10482424-1 Rev.3, PDF pp. 8-10 and Appendix A', 'source viewed; process ledger extracted'),
    ('Sineng 2024','Manufacturer equipment rating 200kVA at 45C, 98kg, max 40 parallel in one group','https://en.si-neng.com/Public/Uploads/uploadfile/files/20240129/EH0200HAM1.pdf','Data sheet, 1-page PDF','source viewed; rate confirmed'),
    ('ENA 2024','Model EH-0200-HA-M register 200kW','https://www.ena-eng.org/gen-ttr/Index?Action=ViewDetail&EID=128595337&tab=search','Legacy Type Test Register listing','register viewed; supporting device check'),
    ('Jasper et al. 2026','BOS-inclusive peer-reviewed container LCA and reference powers; NOT scaled into target station','https://doi.org/10.1039/D5YA00341E','Energy Advances 5, 550-570','publisher article viewed'),
    ('Jasper raw SI','Public original SI workbook, to be admitted only after byte/hash and process inspection','https://zenodo.org/records/17651912','Jasper 2026 SI.xlsx, published MD5 e6bc45da878b8d663a6d870410f8f2b4','repository metadata confirmed; workbook not downloaded in this execution'),
    ('RTS-GMLC official','Official test system and hydro day-ahead semantics','https://github.com/GridMod/RTS-GMLC','RTS_GMLC source repository','background source, NOT a re-run of full annual UC'),
]
with (OUT/'V72_source_register.csv').open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.writer(f);wr.writerow(['source','role','url','locator','evidence_state']);wr.writerows(sources)

summary={
    'project':'BESS power-matched PCS source-reference arithmetic',
    'reported_mass_kg':str(PCS_MASS_KG),
    'rounded_composition_sum_kg':'99',
    'mass_reconciliation':'rounded source entries 99kg vs manufacturer and report total 98kg',
    'single_PCS_material_kgCO2e':str(GHG_MATERIAL),
    'single_PCS_manufacturing_kgCO2e':str(GHG_MANUFACTURE),
    'single_PCS_transport_kgCO2e':str(GHG_TRANSPORT),
    'single_PCS_sum_kgCO2e':str(PER_DEVICE_GHG),
    'scenarios':records,
    'critical_limitations':[ 'source is consultant process estimate, not EPD','geography/time/LCIA not harmonized with BYD and Nortrafo EPD','AC parallel limit requires multi-group engineering','DC voltage and string configuration not matched to proposed module wiring','PCS could have service replacements; installation auxiliary and construction not included','no annual unrestricted UC or GWP100 net result implied'],
}
(OUT/'V72_PCS_audit_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print('PASS: candidate PCS source audit')
for item in records:
    print(item['case'],item['count_PCS'],'PCS', item['PCS_candidate_total_t_CO2e'],'tCO2e; partial cross-product subtotal',item['cross_product_partial_total_t_CO2e'])
