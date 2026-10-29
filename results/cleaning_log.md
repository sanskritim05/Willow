# Cleaning log: NHATS panel for Willow

- Built: 2026-10-06 12:36
- Rounds: 1-14; 18,439 people; 89,087 person-rounds; 85 columns
- Panel: `data/clean/panel.parquet` (respondent data: keep local, never share)

## Files used

| round | sp | tracker | income | covid |
|---|---|---|---|---|
| 1 | NHATS_Round_1_SP_File.dta | NHATS_Round_1_Tracker_File.dta | NHATS_Round_1_Int_Inc_Imp_File.dta | nan |
| 2 | NHATS_Round_2_SP_File_v2.dta | NHATS_Round_2_Tracker_File_v2.dta | nan | nan |
| 3 | NHATS_Round_3_SP_File.dta | NHATS_Round_3_Tracker_File_V2.dta | NHATS_Round_3_Int_Inc_Imp_File.dta | nan |
| 4 | NHATS_Round_4_SP_File.dta | NHATS_Round_4_Tracker_File_V2.dta | nan | nan |
| 5 | NHATS_Round_5_SP_File_V2.dta | NHATS_Round_5_Tracker_File_V3.dta | NHATS_Round_5_Int_Inc_Imp_File.dta | nan |
| 6 | NHATS_Round_6_SP_File_V2.dta | NHATS_Round_6_Tracker_File_V3.dta | nan | nan |
| 7 | NHATS_Round_7_SP_File.dta | NHATS_Round_7_Tracker_File_V2.dta | NHATS_Round_7_Int_Inc_Imp_File.dta | nan |
| 8 | NHATS_Round_8_SP_File.dta | NHATS_Round_8_Tracker_File_V2.dta | nan | nan |
| 9 | NHATS_Round_9_SP_File.dta | NHATS_Round_9_Tracker_File.dta | NHATS_Round_9_Int_Inc_Imp_File.dta | nan |
| 10 | NHATS_Round_10_SP_File.dta | NHATS_Round_10_Tracker_File.dta | nan | NHATS_R10_CV_SP_File.dta |
| 11 | NHATS_Round_11_SP_File_V2.dta | NHATS_Round_11_Tracker_File.dta | NHATS_Round_11_Int_Inc_Imp_File.dta | nan |
| 12 | NHATS_Round_12_SP_File_V3.dta | NHATS_Round_12_Tracker_File.dta | NHATS_R12_Int_Inc_Imp_File_V2.dta | nan |
| 13 | NHATS_Round_13_SP_File_V3.dta | NHATS_Round_13_Tracker_File_V2.dta | NHATS_R13_Int_Inc_Imp_File_V2.dta | nan |
| 14 | NHATS_Round_14_SP_File_V2.dta | NHATS_Round_14_Tracker_File.dta | NHATS_R14_Int_Inc_Imp_File.dta | nan |

## Dementia classification check

68/70 published counts matched exactly.

## Valid codes set to missing by recode rules

| item | recode | raw code | n set to missing |
|---|---|---|---|
| go_outside_help | help_d | 3.0 | 174 |
| get_around_inside_help | help_d | 3.0 | 117 |
| get_out_of_bed_help | help_d | 3.0 | 214 |
| eating_help | help_d | 3.0 | 197 |
| bathing_help | help_d | 3.0 | 374 |
| toileting_help | help_d | 3.0 | 308 |
| dressing_help | help_d | 3.0 | 84 |
| dressing_help | help_d | 9.0 | 174 |
| go_outside_diff | sfdf | 4.0 | 14 |
| go_outside_diff | sfdf | 5.0 | 21 |
| go_outside_diff | sfdf | 6.0 | 60 |
| go_outside_diff | sfdf | 7.0 | 15 |
| go_outside_diff | sfdf | 8.0 | 1842 |
| get_around_inside_diff | sfdf | 4.0 | 15 |
| get_around_inside_diff | sfdf | 5.0 | 32 |
| get_around_inside_diff | sfdf | 6.0 | 41 |
| get_around_inside_diff | sfdf | 7.0 | 18 |
| get_around_inside_diff | sfdf | 8.0 | 292 |
| get_out_of_bed_diff | sfdf | 4.0 | 16 |
| get_out_of_bed_diff | sfdf | 5.0 | 44 |
| get_out_of_bed_diff | sfdf | 6.0 | 63 |
| get_out_of_bed_diff | sfdf | 7.0 | 67 |
| eating_diff | sfdf | 6.0 | 43 |
| eating_diff | sfdf | 7.0 | 27 |
| eating_diff | sfdf | 8.0 | 83 |
| bathing_diff | sfdf | 6.0 | 62 |
| bathing_diff | sfdf | 7.0 | 103 |
| toileting_diff | sfdf | 6.0 | 104 |
| toileting_diff | sfdf | 7.0 | 55 |
| dressing_diff | sfdf | 6.0 | 67 |
| dressing_diff | sfdf | 7.0 | 76 |
| dressing_diff | sfdf | 8.0 | 420 |
| go_outside_device | devi | 3.0 | 15 |
| go_outside_device | devi | 4.0 | 18 |
| go_outside_device | devi | 8.0 | 1842 |
| get_around_inside_device | devi | 3.0 | 264 |
| get_around_inside_device | devi | 4.0 | 18 |
| get_around_inside_device | devi | 8.0 | 292 |
| get_out_of_bed_device | devi | 3.0 | 83 |
| get_out_of_bed_device | devi | 4.0 | 19 |
| eating_device | devi | 3.0 | 236 |
| eating_device | devi | 8.0 | 249 |
| bathing_device | devi | 3.0 | 193 |
| bathing_device | devi | 4.0 | 437 |
| toileting_device | devi | 3.0 | 699 |
| dressing_device | devi | 3.0 | 121 |
| dressing_device | devi | 8.0 | 846 |
| race_eth | race_eth | 5.0 | 26 |
| race_eth | race_eth | 6.0 | 547 |

## Consistency checks

| check | cases |
|---|---|
| duplicate person-round rows | 0 |
| people whose sex changes across rounds | 0 |
| people whose race/ethnicity changes across rounds | 0 |
| rows after a person's death round | 0 |
| non-community rows that still have activity items | 0 |
| community rows: help reported but no difficulty in any activity (allowed, but worth knowing) | 1480 |

## Cohort flow

| step | n |
|---|---|
| sample people, rounds 1-14 | 18439 |
| person-rounds living in the community | 73928 |
| at-risk windows: community at t-1 and t, no help at t | 44805 |
|   ... died before t+1 | 1107 |
|   ... moved into care before t+1 | 506 |
|   ... not interviewed at t+1 (lost) | 7560 |
| analytic windows (outcome observed at home) | 35632 |
