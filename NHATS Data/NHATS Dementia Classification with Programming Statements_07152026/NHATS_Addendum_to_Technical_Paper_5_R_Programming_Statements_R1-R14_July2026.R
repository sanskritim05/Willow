rm(list = ls())
.libPaths()

library(tidyverse)
library(dplyr)
library(haven)
library(epiDisplay)
library(labelled)
library(stringr)
library(foreign)

##USER DIRECTIONS##
#1 - LINE 19: ENTER THE LOCATION AND NAME OF THE SP DATA FILE OF INTEREST
#2 - LINES 24: ENTER THE ROUND NUMBER OF INTEREST
#3 - LINES 29-33: EDIT THE ROUND NUMBER INSIDE THE QUOTATION MARKS
#4 - LINE 234 & 238: ENTER THE NAME OF THE NEW DATA FILE

#1. ENTER DESIRED SP FILE IN THE PARENTHESES
sp <- read_stata ("[Location]/NHATS_Round_14_SP_File.dta")

#2. ENTER WHICH ROUND?

sp <- sp %>% 
  mutate(rnd = 14) 

#3. EDIT ROUND NUMBER INSIDE THE QUOTES 
#(THIS REMOVES THE PREFIXES ON NEEDED VARIABLES ) 
sp <- sp %>% 
  rename_all(~stringr::str_replace(.,"^r14","")) %>%
  rename_all(~stringr::str_replace(.,"^hc14","")) %>% 
  rename_all(~stringr::str_replace(.,"^is14","")) %>% 
  rename_all(~stringr::str_replace(.,"^cp14","")) %>% 
  rename_all(~stringr::str_replace(.,"^cg14",""))

#STARTING IN ROUND 13, THE VARIABLE NAME OF THE CLOCK DRAWING SCORE IS dclkdlnn, 
#RENAME IT BACK TO dclkdraw
if ("dclkdlnn" %in% names(sp) && !("dclkdraw" %in% names(sp))) {
  sp <- sp %>% rename(dclkdraw = dclkdlnn)
}

#ADD R1DAD8DEM AND SET TO -1 FOR ROUND 1 BECAUSE THERE IS NO PRIOR DIAGNOSIS IN R1
sp <- sp %>% 
  mutate(dad8dem = ifelse(rnd == 1, -1, dad8dem))

#SUBSET NEEDED VARIABLES
df<-sp %>% 
  dplyr::select(spid, rnd, dresid, resptype, disescn9, chgthink1, chgthink2, chgthink3, chgthink4, chgthink5, chgthink6, chgthink7, chgthink8, dad8dem,
                speaktosp, todaydat1, todaydat2, todaydat3, todaydat4, todaydat5, presidna1, presidna3, vpname1, vpname3, quesremem, dclkdraw, atdrwclck, 
                dwrdimmrc, dwrdlstnm, dwrddlyrc)

#FIX A ROUND 2 CODING ERROR#
df <- df %>%
  mutate(dwrdimmrc = ifelse(dwrdimmrc==10 & dwrddlyrc==-3 & rnd==2, -3, dwrdimmrc))

#CREATE SELECTED ROUND DEMENTIA CLASSIFICATION VARIABLE 
df <- df %>%
  mutate(demclas  =  ifelse(dresid==3 | dresid==5 | dresid==7, -9, #SET MISSING (RESIDENTIAL CARE FQ ONLY) AND N.A. (NURSING HOME RESIDENTS, DECEASED)
                            ifelse((dresid==4 & rnd==1) | dresid==6 | dresid==8, -1,                #SET MISSING (RESIDENTIAL CARE FQ ONLY) AND N.A. (NURSING HOME RESIDENTS, DECEASED)
                                   ifelse((disescn9==1 | disescn9==7) &           #CODE PROBABLE IF DEMENTIA DIAGNOSIS REPORTED BY SELF OR PROXY*
                                            (resptype==1 | resptype==2), 1, NA))))

#CODE AD8_SCORE*
#INITIALIZE COUNTS TO NOT APPLICABLE*
#ASSIGN VALUES TO AD8 ITEMS IF PROXY AND DEMENTIA CLASS NOT ALREADY ASSIGNED BY REPORTED DIAGNOSIS 
for(i in 1:8){
  df[[paste("ad8_", i, sep = "")]]  <- as.numeric(ifelse(df[[paste("chgthink", i, sep = "")]]==2 & df$resptype==2 & is.na(df$demclas), 0, #PROXY REPORTS NO CHANGE
                                                         ifelse((df[[paste("chgthink", i, sep = "")]]==1 | df[[paste("chgthink", i, sep = "")]] == 3) & df$resptype==2 & is.na(df$demclas), 1, #PROXY REPORTS A CHANGE OR ALZ/DEMENTIA*
                                                                ifelse(df$resptype==2 & is.na(df$demclas), NA, -1))))    #SET TO NA IF IN RES CARE AND demclass=., OTHERWISE AD8 ITEM IS SET TO NOT APPLICABLE                                                                                                                        
}

#INITIALIZE COUNTS TO NOT APPLICABLE*
for(i in 1:8){
  df[[paste("ad8miss_", i, sep = "")]]  <- as.numeric(ifelse(is.na(df[[paste("ad8_", i, sep = "")]]), 1,
                                                             ifelse((df[[paste("ad8_", i, sep = "")]]==0 | df[[paste("ad8_", i, sep = "")]]==1) & df$resptype==2 & is.na(df$demclas), 0, -1)))
}

for(i in 1:8){
  df[[paste("ad8_", i, sep = "")]] <- as.numeric(ifelse(is.na(df[[paste("ad8_", i, sep = "")]]) & is.na(df$demclas) & df$resptype==2, 0, df[[paste("ad8_", i, sep = "")]]))
}

#COUNT AD8 ITEMS
#ROUNDS 2+
df <- df %>%
  mutate(ad8_score = ifelse(resptype==2 & is.na(demclas), (ad8_1 + ad8_2 + ad8_3 + ad8_4 + ad8_5 + ad8_6 + ad8_7 + ad8_8), -1)) %>% 
  #SET PREVIOUS ROUND DEMENTIA DIAGNOSIS BASED ON AD8 TO AD8_SCORE=8 
  mutate(ad8_score = ifelse(dad8dem==1 & resptype==2 & is.na(demclas), 8, ad8_score))  %>% 
  #SET PREVIOUS ROUND DEMENTIA DIAGNOSIS BASED ON AD8 TO AD8_SCORE=8 FOR ROUNDS 4-9
  mutate(ad8_score = ifelse(resptype==2 & dad8dem==-1 & chgthink1==-1 & (rnd>=4 & rnd<=9) & is.na(demclas) , 8, ad8_score)) 

#COUNT MISSING AD8 ITEMS
df <- df %>% 
  mutate(ad8_miss = ifelse(resptype==2 & is.na(demclas),(ad8miss_1+ad8miss_2+ad8miss_3+ad8miss_4+ad8miss_5+ad8miss_6+ad8miss_7+ad8miss_8), -1))

#CODE AD8 DEMENTIA CLASS 
#IF SCORE>=2 THEN MEETS AD8 CRITERIA
#IF SCORE IS 0 OR 1 THEN DOES NOT MEET AD8 CRITERIA
df <- df %>% 
  mutate(ad8_dem = ifelse(ad8_score>=2, 1,
                          ifelse(ad8_score==0 | ad8_score==1 | ad8_miss==8, 2, NA)))

#UPDATE DEMENTIA CLASSIFICATION VARIABLE WITH AD8 CLASS
df <- df %>% 
  #PROBABLE DEMENTIA BASED ON AD8 SCORE  
  mutate(demclas = ifelse(ad8_dem==1 & is.na(demclas), 1, 
                          #NO DIAGNOSIS, DOES NOT MEET AD8 CRITERION, AND PROXY SAYS CANNOT ASK SP COGNITIVE ITEMS*
                          ifelse(ad8_dem==2 & speaktosp==2 & is.na(demclas), 3, demclas)))


####CODE DATE ITEMS AND COUNT 
#CODE ONLY YES/NO RESPONSES: MISSING/NA CODES -1, -9 LEFT MISSING*
#2: NO/DK OR -7: REFUSED RECODED TO : NO/DK/RF*
#****ADD NOTES HERE ABOUT WHAT IS HAPPENING IN ROUNDS 1-3, 5+ VS. ROUND 4 
#*
for(i in 1:5){
  df[[paste("date_item", i, sep = "")]]  <- as.numeric(ifelse(df[[paste("todaydat", i, sep = "")]]==1, 1,
                                                              ifelse(df[[paste("todaydat", i, sep = "")]]==2 | df[[paste("todaydat", i, sep = "")]]== -7, 0, NA)))
}

#COUNT CORRECT DATE ITEMS
df <- df %>% 
  mutate(date_item4 = ifelse(rnd==4, date_item5, date_item4)) %>% 
  mutate(date_sum = date_item1 + date_item2 + date_item3 + date_item4) %>% 
  
  #PROXY SAYS CAN'T SPEAK TO SP
  mutate(date_sum = ifelse(speaktosp==2 & is.na(date_sum),-2,  
                           #PROXY SAYS CAN SPEAK TO SP BUT SP UNABLE TO ANSWER*
                           ifelse((is.na(date_item1) | is.na(date_item2) | is.na(date_item3) | is.na(date_item4)) & speaktosp==1,-3, date_sum))) %>% 
  
  #MISSING IF PROXY SAYS CAN'T SPEAK TO SP*  
  mutate(date_sumr = ifelse(date_sum == -2 , NA, 
                            #0 IF SP UNABLE TO ANSWER*
                            ifelse(date_sum == -3 , 0, date_sum)))


########PRESIDENT AND VICE PRESIDENT NAME ITEMS AND COUNT########## 
##CODE ONLY YES/NO RESPONSES: MISSING/N.A. CODES -1,-9 LEFT MISSING *
##2:NO/DK OR -7:REFUSED RECODED TO 0:NO/DK/RF*
df <- df %>% 
  mutate(preslast = ifelse(presidna1 == 1, 1,
                           ifelse(presidna1 == 2 | presidna1 == -7, 0, NA))) %>% 
  mutate(presfirst = ifelse(presidna3 == 1, 1,
                            ifelse(presidna3 == 2 | presidna3 == -7, 0, NA))) %>% 
  mutate(vplast = ifelse(vpname1 == 1, 1,
                         ifelse(vpname1 == 2 | vpname1 == -7, 0, NA))) %>% 
  mutate(vpfirst = ifelse(vpname3 == 1, 1,
                          ifelse(vpname3 == 2 | vpname3 == -7, 0, NA))) %>% 
  
  #COUNT CORRECT PRESIDENT/VP NAME ITEMS*
  mutate(presvp = preslast + presfirst + vplast + vpfirst) %>% 
  #PROXY SAYS CAN'T SPEAK TO SP 
  mutate(presvp = ifelse(speaktosp == 2 & is.na(presvp), -2, 
                         #PROXY SAYS CAN SPEAK TO SP BUT SP UNABLE TO ANSWER                           
                         ifelse((is.na(preslast) | is.na(presfirst) | is.na(vplast) | is.na(vpfirst)) & speaktosp==1 & is.na(presvp),-3, presvp))) %>% 
  
  #MISSING IF PROXY SAYS CAN’T SPEAK TO SP*
  mutate(presvpr =  ifelse(presvp == -2 , NA, 
                           ifelse(presvp == -3 , 0, presvp))) %>% 
  
  #ORIENTATION DOMAIN: SUM OF DATE RECALL AND PRESIDENT/VP NAMING* 
  mutate(date_prvp = date_sumr + presvpr)


#######EXECUTIVE FUNCTION DOMAIN: CLOCK DRAWING SCORE##########
#RECODE DCLKDRAW TO ALIGN WITH MISSING VALUES IN PREVIOUS ROUNDS (ROUND 10 ONLY)* 
df <- df %>% 
  mutate(dclkdraw = ifelse(speaktosp == 2 & dclkdraw == -9 & rnd==10, -2,
                           ifelse(speaktosp==1 & (quesremem==2 | quesremem==-7 | quesremem==-8) & dclkdraw==-9 & rnd==10, -3,
                                  ifelse(atdrwclck==2 & dclkdraw==-9 & rnd==10, -4,
                                         ifelse(atdrwclck==97 & dclkdraw==-9 & rnd==10, -7, dclkdraw)))))

#RECODE DCLKDRAW TO ALIGN WITH MISSING VALUES IN PREVIOUS ROUNDS (ROUNDS 11 AND FORWARD ONLY)* 
df<-df  %>%
  mutate(dclkdraw = ifelse(speaktosp == 2 & dclkdraw == -9 & rnd>=11, -2, 
                           ifelse(speaktosp == 1 & (quesremem == 2 | quesremem == -7 | quesremem == -8) & dclkdraw == -9, -3 & rnd>=11, dclkdraw))) 
df<-df  %>%
  mutate(clock_scorer = ifelse(dclkdraw == -3 | dclkdraw == -4 | dclkdraw == -7, 0,
                               #IMPUTE MEAN SCORE TO PERSONS MISSING A CLOCK*
                               #IF PROXY SAID CAN ASK SP*
                               ifelse(dclkdraw == -9 & speaktosp == 1, 2, 
                                      #IF SELF-RESPONDENT*       
                                      ifelse(dclkdraw == -9 & speaktosp == -1, 3, 
                                             ifelse(dclkdraw == -2 | dclkdraw == -9, NA, dclkdraw)))))


#MEMORY DOMAIN: IMMEDIATE AND DELAYED WORD RECALL 
df <- df %>%
  mutate(irecall  =  ifelse(dwrdimmrc == -2 | dwrdimmrc == -1, NA,
                            ifelse(dwrdimmrc == -7 | dwrdimmrc == -3, 0, dwrdimmrc))) %>% 
  mutate(irecall = ifelse(rnd==5 & dwrddlyrc==-9, NA, irecall)) %>%  #round 5 only: set cases with missing word list and not previously assigned to missing
  
  mutate(drecall  =  ifelse(dwrddlyrc == -2 | dwrddlyrc == -1, NA,
                            ifelse(dwrddlyrc == -7 | dwrddlyrc == -3, 0, dwrddlyrc))) %>% 
  mutate(drecall = ifelse(rnd==5 & dwrddlyrc==-9, NA, drecall)) %>%  #round 5 only: set cases with missing word list and not previously assigned to missing
  
  mutate(wordrecall0_20 = irecall+drecall)


#CREATE COGNITIVE DOMAINS FOR ALL ELIGIBLE 

df<-df %>% 
  mutate(clock65 = ifelse(clock_scorer == 0 | clock_scorer==1, 1, 
                          ifelse(clock_scorer > 1 & clock_scorer<6, 0, NA)))

df<-df %>%  
  mutate(word65 = ifelse(wordrecall0_20 >= 0 & wordrecall0_20 <=3, 1, 
                         ifelse(wordrecall0_20 > 3 & wordrecall0_20 <=20, 0, NA)))

df<-df %>%  
  mutate(datena65 = ifelse(date_prvp >= 0 & date_prvp <=3, 1, 
                           ifelse(date_prvp > 3 & date_prvp <= 8, 0, NA)))

#  *CREATE COGNITIVE DOMAIN SCORE*
df<-df %>% 
  mutate(domain65 = clock65+word65+datena65)

#*SET CASES WITH MISSING WORD LIST AND NOT PREVIOUSLY ASSIGNED TO MISSING (ROUND 5 ONLY)
df<-df %>%   
  mutate(demclas = ifelse(rnd==5 & dwrdlstnm==-9 & is.na(demclas), -9, demclas))

#UPDATE COGNITIVE CLASSIFICATION*
df<-df %>% 
  #PROBABLE DEMENTIA
  mutate(demclas = ifelse(is.na(demclas) & (speaktosp == 1 | speaktosp == -1) & (domain65==2 | domain65==3), 1,
                          #POSSIBLE DEMENTIA
                          ifelse(is.na(demclas) & (speaktosp == 1 | speaktosp == -1) & domain65==1, 2,
                                 #NO DEMENITA                    
                                 ifelse(is.na(demclas) & (speaktosp == 1 | speaktosp == -1) & domain65==0, 3, demclas))))

#KEEP VARIABLES AND SAVE DATA
df<-df %>% 
  dplyr::select(spid, rnd, demclas)

#CHANGE 14 AFTER "r" TO THE ROUND OF INTEREST
r14demclas <- df

#4. NAME AND SAVE DEMENTIA DATA FILE:
#CHANGE 14 AFTER "r" TO THE ROUND OF INTEREST
save(r14demclas, file = "[file location]/NHATS_cognition_r14.RDa")   

table(df$demclas, useNA = "ifany")








