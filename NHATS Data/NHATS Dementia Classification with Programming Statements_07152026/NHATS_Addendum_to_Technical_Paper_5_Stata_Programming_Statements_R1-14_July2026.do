set mem 500m
set more off

*#1. CREATE MACRO CONTAINAING THE LOCATION AND FILE NAME OF THE ORIGINAL SP DATA FILES OF INTEREST**
global Round1 "...NHATS_Round_1_SP_File.dta"
global Round2 "...NHATS_Round_2_SP_File_v2.dta"
global Round3 "...NHATS_Round_3_SP_File.dta"
global Round4 "...NHATS_Round_4_SP_File.dta"
global Round5 "...NHATS_Round_5_SP_File_V2.dta" 
global Round6 "...NHATS_Round_6_SP_File_V2.dta"  
global Round7 "...NHATS_Round_7_SP_File.dta"  
global Round8 "...NHATS_Round_8_SP_File.dta"  
global Round9 "...NHATS_Round_9_SP_File.dta"  
global Round10 "...NHATS_Round_10_SP_File.dta"  
global Round11 "...NHATS_Round_11_SP_File.dta"  
global Round12 "...NHATS_Round_12_SP_File_V2.dta"  
global Round13 "...NHATS_Round_13_SP_File_V2.dta" 
global Round14 "...NHATS_Round_14_SP_File.dta" 


*#2. CREATE MACRO CONTAINAING THE LOCATION AND FILE NAME OF THE RECODED COGNITION DATA**
global Round1d "...NHATS_Round_1_dementia1.dta"
global Round2d "...NHATS_Round_2_dementia2.dta"
global Round3d "...NHATS_Round_3_dementia3.dta"
global Round4d "...NHATS_Round_4_dementia4.dta"
global Round5d "...NHATS_Round_5_dementia5.dta" 
global Round6d "...NHATS_Round_6_dementia6.dta"  
global Round7d "...NHATS_Round_7_dementia7.dta"  
global Round8d "...NHATS_Round_8_dementia8.dta"  
global Round9d "...NHATS_Round_9_dementia9.dta"  
global Round10d "...NHATS_Round_10_dementia10.dta"  
global Round11d "...NHATS_Round_11_dementia11.dta"
global Round12d "...NHATS_Round_12_dementia12.dta"
global Round13d "...NHATS_Round_13_dementia13.dta"
global Round14d "...NHATS_Round_14_dementia14.dta"


*#3. IN NUMLIST, ENTER THE ROUNDS OF INTEREST (1 through 14)
foreach num of numlist 1/14 {
use "${Round`num'}", clear  
	rename r`num'* *
	rename hc`num'* *
	rename is`num'* *
	rename cp`num'* *
	rename cg`num'* *
	gen round=`num'

*STARTING IN ROUND 13, THE VARIABLE NAME OF THE CLOCK DRAWING SCORE IS dclkdlnn, 
*RENAME IT BACK TO dclkdraw
if `num' >= 13 {
    capture confirm variable dclkdlnn
    if _rc == 0 {
        capture drop dclkdraw
        rename dclkdlnn dclkdraw
    }
}
	
*ADD DAD8DEM1=-1 TO ROUND 1 AND DAD8DEMX=dad8dem TO ROUND X BECAUSE THERE IS NO PRIOR DIAGNOSIS IN R1
if round==1 {
		gen dad8dem`num'=-1
	}
	else if round>=2 {
		gen dad8dem`num'=dad8dem
	}
	
*FIX ROUND 2 CODING ERROR*
replace dwrdimmrc=-3 if dwrdimmrc==10 & dwrddlyrc==-3 & round==2

*CREATE DEMENTIA CLASSIFICATION VARIABLE*
*SET MISSING (RESIDENTIAL CARE FQ ONLY) AND N.A. (NURSING HOME RESIDENTS, DECEASED) - *
gen demclas=-9 if dresid==7 | dresid==3 | dresid==5 & round>=2
replace demclas=-9 if dresid==3 & round==1
replace demclas=-1 if dresid==6 |dresid==8 & round>=2
replace demclas=-1 if dresid==4 & round==1

*CODE PROBABLE IF DEMENTIA DIAGNOSIS REPORTED BY SELF OR PROXY* 
replace demclas=1 if (disescn9==1) & (resptype==1 | resptype==2) & round==1
replace demclas=1 if (disescn9==1 | disescn9==7) & (resptype==1 | resptype==2) & round>=2
tab demclas

*CODE AD8_SCORE*
*INITIALIZE COUNTS TO NOT APPLICABLE*
*ASSIGN VALUES TO AD8 ITEMS IF PROXY AND DEMENTIA CLASS NOT ALREADY ASSIGNED BY REPORTED DIAGNOSIS
foreach no of numlist 1/8 {
     *INITIALIZE COUNTS TO NOT APPLICABLE*
	 gen ad8_`no'=-1	 
	 replace ad8_`no'=. if resptype==2 & demclas==.
	 *PROXY REPORTS A CHANGE OR ALZ/DEMENTIA*
     replace ad8_`no'=1 if resptype==2 & demclas==. & (chgthink`no'==1 | chgthink`no'==3) 
	 *PROXY REPORTS NO CHANGE*
     replace ad8_`no'=0 if resptype==2 & demclas==. & (chgthink`no'==2) & ad8_`no'==. 
}

foreach no of numlist 1/8 {
	*INITIALIZE COUNTS TO NOT APPLICABLE*
	gen ad8miss_`no'=-1
	replace ad8miss_`no'=0 if resptype==2 & demclas==. & (ad8_`no'==0 | ad8_`no'==1)
    replace ad8miss_`no'=1 if resptype==2 & demclas==. & ad8_`no'==.
	replace ad8_`no'=0 if resptype==2 & demclas==. & ad8_`no'==.
} 

*COUNT AD8 ITEMS*
gen ad8_score=-1
replace ad8_score=(ad8_1+ad8_2+ad8_3+ad8_4+ad8_5+ad8_6+ad8_7+ad8_8) if resptype==2 & demclas==. 
*SET PREVIOUS ROUND DEMENTIA DIAGNOSIS BASED ON AD8 TO AD8_SCORE=8*
replace ad8_score=8 if dad8dem`num'==1 & resptype==2 & demclas==. & round>=2
*USE THE FOLLOWING LINE FOR ROUNDS 4-9 ONLY*
replace ad8_score=8 if resptype==2 & dad8dem`num'==-1 & chgthink1==-1 & demclas==. & (round>=4 & round<=9)

*COUNT MISSING AD8 ITEMS*         
gen ad8_miss= -1
replace ad8_miss=(ad8miss_1+ad8miss_2+ad8miss_3+ad8miss_4+ad8miss_5+ad8miss_6+ad8miss_7+ad8miss_8) if resptype==2 & demclas==. 

*CODE AD8 DEMENTIA CLASS*
*IF SCORE>=2 THEN MEETS AD8 CRITERIA*
gen ad8_dem=1 if ad8_score>=2 
*IF SCORE IS 0 OR 1 THEN DOES NOT MEET AD8 CRITERIA*
replace ad8_dem=2 if (ad8_score==0 | ad8_score==1 | ad8_miss==8) & ad8_dem==.

*UPDATE DEMENTIA CLASSIFICATION VARIABLE WITH AD8 CLASS*
*PROBABLE DEMENTIA BASED ON AD8 SCORE*
replace demclas=1 if ad8_dem==1 & demclas==.

*NO DIAGNOSIS, DOES NOT MEET AD8 CRITERION, AND PROXY SAYS CANNOT ASK SP COGNITIVE ITEMS*
replace demclas=3 if ad8_dem==2 & speaktosp==2 & demclas==.

*CODE DATE ITEMS AND COUNT*
foreach no of numlist 1/5 {
	*CODE ONLY YES/NO RESPONSES: MISSING/NA CODES -1, -9 LEFT MISSING*
	gen date_item`no'=todaydat`no' if todaydat`no'>0 
	*2: NO/DK OR -7: REFUSED RECODED TO : NO/DK/RF*
	replace date_item`no'=0 if todaydat`no'==2 | todaydat`no'==-7
}

*COUNT CORRECT DATE ITEMS*
*USE THE FOLLOWING CODE FOR ROUNDS OTHER THAN 4*
gen date_sum=date_item1 + date_item2 + date_item3 + date_item4 if round~=4
*USE THE FOLLOWING CODE FOR ROUND 4*
replace date_sum=date_item1 + date_item2 + date_item3 + date_item5 if round==4

*PROXY SAYS CAN'T SPEAK TO SP*
replace date_sum=-2 if date_sum==. & speaktosp==2
*PROXY SAYS CAN SPEAK TO SP BUT SP UNABLE TO ANSWER*
replace date_sum=-3 if (date_item1==. | date_item2==. | date_item3==. | date_item4==.) & speaktosp==1

gen date_sumr=date_sum
*MISSING IF PROXY SAYS CAN'T SPEAK TO SP*
replace date_sumr=. if date_sum==-2
*0 IF SP UNABLE TO ANSWER*
replace date_sumr=0 if date_sum==-3


*PRESIDENT AND VICE PRESIDENT NAME ITEMS AND COUNT*
** CODE ONLY YES/NO RESPONSES: MISSING/N.A. CODES -1,-9 LEFT MISSING *
*2:NO/DK OR -7:REFUSED RECODED TO 0:NO/DK/RF*
gen preslast=presidna1 if presidna1>0
replace preslast=0 if presidna1==-7 | presidna1==2

gen presfirst=presidna3 if presidna3>0
replace presfirst=0 if presidna3==-7 | presidna3==2

gen vplast=vpname1 if vpname1>0
replace vplast=0 if vpname1==-7 | vpname1==2

gen vpfirst=vpname3 if vpname3>0
replace vpfirst=0 if vpname3==-7 | vpname3==2

*COUNT CORRECT PRESIDENT/VP NAME ITEMS*
gen presvp= preslast+presfirst+vplast+vpfirst
** PROXY SAYS CAN'T SPEAK TO SP *
replace presvp=-2 if presvp==. & speaktosp==2
** PROXY SAYS CAN SPEAK TO SP BUT SP UNABLE TO ANSWER *
replace presvp=-3 if presvp==. & speaktosp==1 & (preslast==. | presfirst==. | vplast==. | vpfirst==.)

gen presvpr=presvp
*MISSING IF PROXY SAYS CAN’T SPEAK TO SP*
replace presvpr=. if presvp==-2
*0 IF SP UNABLE TO ANSWER*
replace presvpr=0 if presvp==-3


*ORIENTATION DOMAIN: SUM OF DATE RECALL AND PRESIDENT/VP NAMING* 
gen date_prvp=date_sumr + presvpr

*EXECUTIVE FUNCTION DOMAIN: CLOCK DRAWING SCORE*
*RECODE CG#DCLKDRAW TO ALIGN WITH MISSING VALUES IN PREVIOUS ROUNDS (ROUND 10 ONLY)*
replace dclkdraw=-2 if speaktosp==2 & dclkdraw==-9 & round==10
replace dclkdraw=-3 if speaktosp==1 & (quesremem==2 | quesremem==-7 | quesremem==-8) & dclkdraw==-9 & round==10
replace dclkdraw=-4 if atdrwclck==2 & dclkdraw==-9 & round==10
replace dclkdraw=-7 if atdrwclck==97 & dclkdraw==-9 & round==10

*RECODE cg`num'DCLKDRAW TO ALIGN WITH MISSING VALUES IN PREVIOUS ROUNDS (ROUNDS 11 AND FORWARD ONLY)*
replace dclkdraw=-2 if speaktosp==2 & dclkdraw==-9 & round>=11
replace dclkdraw=-3 if speaktosp==1 & (quesremem==2 | quesremem==-7 | quesremem==-8) & dclkdraw==-9 & round>=11

gen clock_scorer=dclkdraw
replace clock_scorer=. if dclkdraw==-2 | dclkdraw==-9
replace clock_scorer=0 if dclkdraw==-3 | dclkdraw==-4 | dclkdraw==-7
*IMPUTE MEAN SCORE TO PERSONS MISSING A CLOCK*
*IF PROXY SAID CAN ASK SP*
replace clock_scorer=2 if dclkdraw==-9 & speaktosp==1
*IF SELF-RESPONDENT*
replace clock_scorer=3 if dclkdraw==-9 & speaktosp==-1

*MEMORY DOMAIN: IMMEDIATE AND DELAYED WORD RECALL*
gen irecall=dwrdimmrc
replace irecall=. if dwrdimmrc==-2 | dwrdimmrc==-1
replace irecall=0 if dwrdimmrc==-7 | dwrdimmrc==-3
*SET CASES WITH MISSING WORD LIST AND NOT PREVIOUSLY ASSIGNED TO MISSING (ROUND 5 ONLY)
replace irecall=. if dwrdimmrc==-9 & round==5

gen drecall=dwrddlyrc
replace drecall=. if dwrddlyrc==-2 | dwrddlyrc==-1
replace drecall=0 if dwrddlyrc==-7 | dwrddlyrc==-3
*SET CASES WITH MISSING WORD LIST AND NOT PREVIOUSLY ASSIGNED TO MISSING (ROUND 5 ONLY)
replace drecall=. if dwrddlyrc==-9 & round==5

gen wordrecall0_20=irecall+drecall


*CREATE COGNITIVE DOMAINS FOR ALL ELIGIBLE*
gen clock65=0 if clock_scorer>1 & clock_scorer<=5
replace clock65=1 if clock_scorer>=0 & clock_scorer<=1

gen word65=0 if wordrecall0_20>3 & wordrecall0_20<=20
replace word65=1 if wordrecall0_20>=0 & wordrecall0_20<=3

gen datena65=0 if date_prvp>3 & date_prvp<=8
replace datena65=1 if date_prvp>=0 & date_prvp<=3

*CREATE COGNITIVE DOMAIN SCORE*
gen domain65 = clock65+word65+datena65

*SET CASES WITH MISSING WORD LIST AND NOT PREVIOUSLY ASSIGNED TO MISSING (ROUND 5 ONLY)
replace demclas=-9 if dwrdlstnm==-9 & demclas==. & round==5

*UPDATE COGNITIVE CLASSIFICATION*
*PROBABLE DEMENTIA*
replace demclas=1 if demclas==. & (speaktosp==1 | speaktosp==-1) & (domain65==2 | domain65==3)
*POSSIBLE DEMENTIA*
replace demclas=2 if demclas==. & (speaktosp==1 | speaktosp==-1) & domain65==1
*NO DEMENTIA*
replace demclas=3 if demclas==. & (speaktosp==1 | speaktosp==-1) & domain65==0

*Label variables and values*
label variable ad8_dem "R`num' Dementia classification based on proxy AD8 report" 
label define ad8_dem_values 1 "1 Meets dementia criteria" 2 "2 Does not meet dementia criteria"
label values ad8_dem ad8_dem_values
label variable demclas "R`num' NHATS Dementia Classification"
label define dementialabel656 1 "1 Probable dementia" 2 "2 Possible dementia" 3 "3 No dementia" -1 "-1 Deceased or nursing home resident in initial round" -9 "-9 Missing"
label values demclas dementialabel656
label define domain_labels6 0 "0 Does not meet criteria" 1 "1 Meets criteria"
label values clock65 word65 datena65 domain_labels6
label define domain65_labels6 0 "0 Not impaired" 1 "Impaired in 1 domain" 2 "Impaired in 2 domains" 3 "Impaired in 3 domains"
label values domain65 domain65_labels6
tab demclas dresid
tab demclas

rename demclas r`num'demclas

save "${Round`num'd}", replace
}

