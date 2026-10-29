proc format;
value demclas
 1="1:Probable dementia"
 2="2:Possible dementia"
 3="3:No dementia"
 -1="-1:Deceased or nursing home resident in initial round"
 -9="-9:Missing"
 ;
value ad8dem
 1="1:Meets dementia criteria"
 2="2:Does not meet dementia criteria"
 ;
value domain_l
0="0:Does not meet criteria"
1="1:Meets criteria"
;
value domain65_l
0="0 Not impaired" 
1="Impaired in 1 domain" 
2="Impaired in 2 domains" 
3="Impaired in 3 domains"
;
run;


libname demclas "[LOCATION TO SAVE NEW DATA]";


%macro dementia1to14(rd, path, dataname, formatfile);


libname nhatsr&rd "&path";
%include "&path\&formatfile..sas";

data demclas.Round&rd;

*STARTING IN ROUND 13, THE VARIABLE NAME OF THE CLOCK DRAWING SCORE IS dclkdlnn, 
*RENAME IT BACK TO dclkdraw;
%if &rd >= 13 %then %do;
  set nhatsr&rd..&dataname(rename=(cg&rd.dclkdlnn=cg&rd.dclkdraw));
%end;
%else %do;
  set nhatsr&rd..&dataname;
%end;


** DATE STEP CODE FOR CREATING DEMENTIA CLASSIFICATION VARIABLE **;
length r&rd.demclas
 r&rd.ad8_dem r&rd.ad8_1-r&rd.ad8_8 r&rd.ad8miss_1-r&rd.ad8miss_8 r&rd.ad8_score r&rd.ad8_miss
 r&rd.date_mon r&rd.date_day r&rd.date_yr r&rd.date_dow r&rd.date_sum r&rd.date_sumr
 r&rd.preslast r&rd.presfirst r&rd.vplast r&rd.vpfirst r&rd.presvp r&rd.presvpr r&rd.date_prvp
 r&rd.clock_scorer r&rd.irecall r&rd.drecall r&rd.wordrecall0_20
 r&rd.clock65 r&rd.word65 r&rd.datena65 r&rd.domain65
 3;
label r&rd.demclas="R&rd. NHATS Dementia Classification";

%if &rd = 2 %then %do;
	if cg2dwrdimmrc = 10 and cg2dwrddlyrc = -3  then  cg2dwrdimmrc = -3; **USE THIS LINE TO FIX A CODING ERROR IN ROUND 2 ONLY**;
%end; 

%if &rd = 1 %then %do;
** 1) SET MISSING (RESIDENTIAL CARE FQ ONLY) AND N.A. (NURSING HOME RESIDENTS) **;
	if r1dresid=3 then r1demclas=-9 ;
	if r1dresid=4 then r1demclas=-1 ;
%end; 

%if &rd ne 1 %then %do;
** 1) SET MISSING (RESIDENTIAL CARE FQ ONLY) AND N.A. (NURSING HOME RESIDENTS, DECEASED) **;
	if r&rd.dresid in (3,5,7) then r&rd.demclas=-9;
	if r&rd.dresid in (6,8) then r&rd.demclas=-1;
%end; 

** 2) CODE PROBABLE IF DEMENTIA DIAGNOSIS REPORTED BY SELF OR PROXY **;
if hc&rd.disescn9 in (1,7) and is&rd.resptype in (1,2) then r&rd.demclas=1;

** 3a) CODE AD8_SCORE **;
array r&rd.think {*} cp&rd.chgthink1-cp&rd.chgthink8; ** QUESTIONNAIRE ITEMS **;
array r&rd.ad8item {*} r&rd.ad8_1-r&rd.ad8_8;
array r&rd.ad8miss {*} r&rd.ad8miss_1-r&rd.ad8miss_8;
 r&rd.ad8_score =-1;
 r&rd.ad8_miss =-1;

 do i=1 to dim(r&rd.ad8item);
 ** INITIALIZE COUNTS TO NOT APPLICABLE**;
 r&rd.ad8item{i}=-1;
 r&rd.ad8miss{i}=-1;
 ** ASSIGN VALUES TO AD8 ITEMS IF PROXY AND DEMENTIA CLASS NOT ALREADY ASSIGNED BY
REPORTED DIAGNOSIS **;
 if is&rd.resptype=2 and r&rd.demclas=. then do;
 r&rd.ad8item{i}=.;
 if r&rd.think{i} in (1,3) then r&rd.ad8item{i}=1; ** PROXY REPORTS A CHANGE OR ALZ/DEMENTIA **;
 else if r&rd.think{i}=2 then r&rd.ad8item{i}=0; ** PROXY REPORTS NO CHANGE **;
 r&rd.ad8_score=sum(of r&rd.ad8item{*}); ** COUNT AD8 ITEMS **;

 if r&rd.ad8item{i} in (0,1) then r&rd.ad8miss{i}=0;
 else if r&rd.ad8item{i}=. then r&rd.ad8miss{i}=1;
 r&rd.ad8_miss=sum(of r&rd.ad8miss{*}); ** COUNT MISSING AD8 ITEMS **;
 end;
 end;
** 3b) CODE AD8 DEMENTIA CLASS **;

%if &rd ne 1 %then %do;
if cp&rd.dad8dem=1 and is&rd.resptype=2 and r&rd.demclas=. then r&rd.ad8_score=8; 
%end;

**USE THIS LINE FOR ROUNDS 4-9 ONLY**;
%if &rd = 4 or &rd = 5 or &rd = 6  or &rd = 7  or &rd = 8 or &rd = 9 %then %do;
if is&rd.resptype=2 and cp&rd.dad8dem=-1 and cp&rd.chgthink1=-1 and r&rd.demclas=. then r&rd.ad8_score=8;
%end;

if r&rd.ad8_score>=2 then r&rd.ad8_dem=1 ; ** IF SCORE >=2 THEN MEETS AD8 CRITERION **;
if (r&rd.ad8_score in (0,1) or r&rd.ad8_miss=8) and r&rd.ad8_dem=. then r&rd.ad8_dem=2; ** IF SCORE IS 0 OR 1 OR ALL ITEMS MISSING THEN DOES NOT MEET AD8 CRITERION **;
** 4) UPDATE DEMENTIA CLASSIFICATION VARIABLE WITH AD8 CLASS **;
if r&rd.demclas=. then do;
 if r&rd.ad8_dem=1 then r&rd.demclas=1; ** PROBABLE BASED ON AD8 SCORE **;
 if r&rd.ad8_dem=2 and cg&rd.speaktosp=2 then r&rd.demclas=3; ** NO DIAGNOSIS, DOES NOT MEET AD8
CRITERION, AND PROXY SAYS CANNOT ASK SP COGNITIVE ITEMS **;
end;
** 5) CODE DATE ITEMS AND COUNT **;

%if &rd ne 4 %then %do;
array cg&rd.date {*} cg&rd.todaydat1-cg&rd.todaydat4; **USE THIS LINE FOR ROUNDS 1-3 and 5-11**;
%end; 

%if &rd = 4 %then %do;
array cg4date {*} cg4todaydat1 cg4todaydat2 cg4todaydat3 cg4todaydat5; **USE THIS LINE FOR ROUND 4**;
%end; 

array r&rd.date_item {*} r&rd.date_mon r&rd.date_day r&rd.date_yr r&rd.date_dow;


do i=1 to dim(r&rd.date_item);
 if cg&rd.date{i} > 0 then r&rd.date_item{i}=cg&rd.date{i}; *** CODE ONLY YES/NO RESPONSES: MISSING/N.A.
CODES -1,-9 LEFT MISSING **;
 if cg&rd.date{i} in (-7,2) then r&rd.date_item{i}=0; ** 2:NO/DK OR -7:REFUSED RECODED TO 0:NO/DK/RF
**;
 r&rd.date_sum=sum(of r&rd.date_item{*}); ** COUNT CORRECT DATE ITEMS
**;
end;

if r&rd.date_sum=. then do;
 if cg&rd.speaktosp=2 then r&rd.date_sum=-2; ** PROXY SAYS CAN'T SPEAK TO SP
**;
 else if cg&rd.speaktosp=1 and max(of cg&rd.date{*})=-1 then r&rd.date_sum=-3; ** PROXY SAYS CAN SPEAK TO
SP BUT SP UNABLE TO ANSWER **;
end;

r&rd.date_sumr=r&rd.date_sum;
if r&rd.date_sum=-2 then r&rd.date_sumr=.; ** MISSING IF PROXY SAYS CAN'T SPEAK TO SP
**;
else if r&rd.date_sum=-3 then r&rd.date_sumr=0; ** 0 IF SP UNABLE TO ANSWER **;
** 6) PRESIDENT AND VICE PRESIDENT NAME ITEMS AND COUNT **;
array cg&rd.pres {*} cg&rd.presidna1 cg&rd.presidna3 cg&rd.vpname1 cg&rd.vpname3;
array r&rd.pres_item {*} r&rd.preslast r&rd.presfirst r&rd.vplast r&rd.vpfirst;
do i=1 to dim(r&rd.pres_item);
 if cg&rd.pres{i} > 0 then r&rd.pres_item{i}=cg&rd.pres{i}; ** CODE ONLY YES/NO RESPONSES: MISSING/N.A. CODES
-1,-9 LEFT MISSING **;
 if cg&rd.pres{i} in (-7,2) then r&rd.pres_item{i}=0; ** 2:NO/DK OR -7:REFUSED RECODED TO 0:NO/DK/RF
**;
 r&rd.presvp=sum(of r&rd.pres_item{*}); ** COUNT CORRECT PRESIDENT/VEEP NAME ITEMS
**;
end;
if r&rd.presvp=. then do;
 if cg&rd.speaktosp=2 then r&rd.presvp=-2; ** PROXY SAYS CAN'T SPEAK TO SP
**;
 else if cg&rd.speaktosp=1 and max(of cg&rd.pres{*})=-1 then r&rd.presvp=-3; ** PROXY SAYS CAN SPEAK TO SP
BUT SP UNABLE TO ANSWER **;
end;
r&rd.presvpr=r&rd.presvp;
if r&rd.presvp=-2 then r&rd.presvpr=.; ** MISSING IF PROXY SAYS CAN'T SPEAK TO SP **;
else if r&rd.presvp=-3 then r&rd.presvpr=0; ** 0 IF SP UNABLE TO ANSWER **;
** 7) ORIENTATION DOMAIN: SUM OF DATE RECALL AND PRESIDENT NAMING **;
r&rd.date_prvp=sum(r&rd.date_sumr,r&rd.presvpr);

** 8) EXECUTIVE FUNCTION DOMAIN: CLOCK DRAWING SCORE **;
*RECODE CLOCK DRAWING SCORE TO ALIGN WITH MISSING VALUES IN PREVIOUS ROUNDS (ROUNDS 11 AND FORWARD ONLY)*;
%if &rd >= 11 %then %do;
  if cg&rd.speaktosp=2 and cg&rd.dclkdraw=-9 then cg&rd.dclkdraw=-2;
  if cg&rd.speaktosp=1 and cg&rd.quesremem in (2, -7, -8) and cg&rd.dclkdraw=-9 then cg&rd.dclkdraw=-3;
%end;


%if &rd = 10 %then %do;
	if cg10speaktosp=2 and cg10dclkdraw=-9 then cg10dclkdraw=-2;
	if cg10speaktosp=1 and cg10quesremem in (2, -7, -8) and cg10dclkdraw=-9 then cg10dclkdraw=-3;
	if cg10atdrwclck=2  and cg10dclkdraw=-9 then cg10dclkdraw=-4;
	if cg10atdrwclck=97 and cg10dclkdraw=-9 then cg10dclkdraw=-7;
%end;

r&rd.clock_scorer=cg&rd.dclkdraw;
if cg&rd.dclkdraw in (-2,-9) then r&rd.clock_scorer=.;
if cg&rd.dclkdraw in (-3,-4,-7) then r&rd.clock_scorer=0;

** IMPUTE MEAN SCORE TO PERSONS MISSING A CLOCK **;
if cg&rd.dclkdraw=-9 and cg&rd.speaktosp=1 then r&rd.clock_scorer=2; ** IF PROXY SAID CAN ASK SP **;
if cg&rd.dclkdraw=-9 and cg&rd.speaktosp=-1 then r&rd.clock_scorer=3; ** IF SELF RESPONDENT **;


** 9) MEMORY DOMAIN: IMMEDIATE AND DELAYED WORD RECALL **;
array cg&rd.recall {*} cg&rd.dwrdimmrc cg&rd.dwrddlyrc;
array r&rd.word_recall {*} r&rd.irecall r&rd.drecall;
do i=1 to dim(r&rd.word_recall);
 r&rd.word_recall{i}=cg&rd.recall{i};
 if cg&rd.recall{i} in (-2,-1) then r&rd.word_recall{i}=.;
 if cg&rd.recall{i} in (-7,-3) then r&rd.word_recall{i}=0;

**SET CASES WITH MISSING WORD LIST AND NOT PREVIOUSLY ASSIGNED TO MISSING (ROUND 5 ONLY)**;
%if &rd = 5 %then %do;
	if cg5dwrdimmrc=-9 then r5word_recall{i}=.;
%end;

 r&rd.wordrecall0_20=sum(of r&rd.word_recall{*});
end;

** 10) CREATE COGNITIVE DOMAINS FOR ALL ELIGIBLE **;
** I.E. PROXY BUT PROXY SAYS CAN ASK SP, NOT FQ ONLY, NOT NH **;
if (1 < r&rd.clock_scorer) and (r&rd.clock_scorer <= 5) then r&rd.clock65=0;
if (0 <= r&rd.clock_scorer) and (r&rd.clock_scorer <= 1) then r&rd.clock65=1;

if (3 < r&rd.wordrecall0_20) and (r&rd.wordrecall0_20 <= 20) then r&rd.word65=0;
if (0 <= r&rd.wordrecall0_20) and (r&rd.wordrecall0_20 <= 3)  then r&rd.word65=1;

if (3 < r&rd.date_prvp) and (r&rd.date_prvp <= 8) then r&rd.datena65=0;
if (0 <= r&rd.date_prvp) and (r&rd.date_prvp <= 3) then r&rd.datena65=1;

** 10) CREATE COGNITIVE DOMAIN SCORE **;
array r&rd.domains {*} r&rd.clock65 r&rd.word65 r&rd.datena65;
do i=1 to dim(r&rd.domains);
 r&rd.domain65=r&rd.clock65 + r&rd.word65 + r&rd.datena65;
end; 


**SET CASES WITH MISSING WORD LIST AND NOT PREVIOUSLY ASSIGNED TO MISSING (ROUND 5 ONLY)**;
%if &rd = 5 %then %do;
	if cg5dwrdlstnm=-9 and r5demclas=. then r5demclas=-9;
%end;

** 11) UPDATE COGNITIVE CLASSIFICATION **;
if r&rd.demclas=. and cg&rd.speaktosp in (-1,1) then do;
if 2 <= r&rd.domain65 <=3 then r&rd.demclas=1; ** PROBABLE DEMENTIA **;
if r&rd.domain65 =1 then r&rd.demclas=2; ** POSSIBLE DEMENTIA **;
if r&rd.domain65 =0 then r&rd.demclas=3; ** NO DEMENTIA **;
end;



*KEEP DEMENTIA CLASSIFICATION AND COMPONENTS*;
keep spid r&rd.demclas r&rd.domain65 r&rd.ad8_dem r&rd.clock65 r&rd.word65 r&rd.datena65;

format 
r&rd.demclas demclas. 
r&rd.ad8_dem  ad8dem. 
r&rd.clock65 r&rd.word65 r&rd.datena65 domain_l. 
r&rd.domain65 domain65_l.;


run;


proc freq data = demclas.Round&rd;
table  r&rd.demclas ;
run;


%mend;  

%dementia1to14(14,
[LOCATION WHERE ROUND 14 DATA IS SAVED],
NHATS_Round_14_SP_File,
NHATS_Round_13_Combined_PROC_FORMAT_Statement_V2)

%dementia1to14(13,
[LOCATION WHERE ROUND 13 DATA IS SAVED],
NHATS_Round_13_SP_File_V2,
NHATS_Round_13_Combined_PROC_FORMAT_Statement)

%dementia1to14(12,
[LOCATION WHERE ROUND 12 DATA IS SAVED],
NHATS_Round_12_SP_File_V2,
NHATS_Round_12_Combined_PROC_FORMAT_Statement_V2)

%dementia1to14(11,
[LOCATION WHERE ROUND 11 DATA IS SAVED],
NHATS_Round_11_SP_File,
NHATS_Round_11_Combined_PROC_FORMAT_Statement)

%dementia1to14(10,
[LOCATION WHERE ROUND 10 DATA IS SAVED],
NHATS_Round_10_SP_File,
NHATS_Round_10_Combined_PROC_FORMAT_Statement)

%dementia1to14(9,
[LOCATION WHERE ROUND 9 DATA IS SAVED],
NHATS_Round_9_SP_File,
NHATS_Round_9_Combined_PROC_FORMAT_Statement)

%dementia1to14(8,
[LOCATION WHERE ROUND 8 DATA IS SAVED],
NHATS_Round_8_SP_File,
NHATS_Round_8_Combined_PROC_FORMAT_Statement)

%dementia1to14(7,
[LOCATION WHERE ROUND 7 DATA IS SAVED],
NHATS_Round_7_SP_File,
NHATS_Round_7_Combined_PROC_FORMAT_Statement)

%dementia1to14(6,
[LOCATION WHERE ROUND 6 DATA IS SAVED],
NHATS_Round_6_SP_File_V2,
NHATS_Round_6_Combined_PROC_FORMAT_Statement_V2)

%dementia1to14(5,
[LOCATION WHERE ROUND 5 DATA IS SAVED],
NHATS_Round_5_SP_File_v2,
NHATS_Round_5_Combined_PROC_FORMAT_Statement_V2)

%dementia1to14(4,
[LOCATION WHERE ROUND 4 DATA IS SAVED],
NHATS_Round_4_SP_File,
NHATS_Round_4_Combined_PROC_FORMAT_Statement)

%dementia1to14(3,
[LOCATION WHERE ROUND 3 DATA IS SAVED],
NHATS_Round_3_SP_File,
NHATS_Round_3_Combined_PROC_FORMAT_Statement)

%dementia1to14(2,
[LOCATION WHERE ROUND 2 DATA IS SAVED],
NHATS_Round_2_SP_File_v2,
NHATS_Round_2_Combined_PROC_FORMAT_Statement_v2)

%dementia1to14(1,
[LOCATION WHERE ROUND 1 DATA IS SAVED],
NHATS_Round_1_SP_File,
Proc Format)







