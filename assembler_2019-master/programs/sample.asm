# Lovingly crafted by robots
# 2018-05-23 11:05:16.838269 from programs/sample.dl
#
   LOAD r1,const24_4
   LOAD r2,const3_5
   SUB  r1,r1,r2
  SUB  r0,r1,r0 
  JUMP/Z elsewpart_2
   LOAD r1,const17_7
   LOAD r2,y_8
   ADD  r1,r1,r2
  STORE  r1,x_6
   LOAD r1,const34_9
   LOAD r2,x_6
   MUL  r1,r1,r2
   LOAD r2,const4_10
   ADD  r1,r1,r2
  STORE  r1,y_8
  JUMP endif_3
elsewpart_2: 
endif_3: #endif
loop_11:  #While loop
   LOAD r1,const14_13
  SUB  r0,r1,r0 
  JUMP/Z endloop_12
   LOAD r1,const21_14
  STORE  r1,x_6
   LOAD r1,const5_16
   LOAD r2,const3_5
   ADD  r1,r1,r2
   LOAD r2,const4_10
   MUL  r1,r1,r2
  STORE  r1,z_15
  JUMP loop_11
endloop_12: 
  HALT  r0,r0,r0
x_6: DATA 0 #x
y_8: DATA 0 #y
z_15: DATA 0 #z
const24_4:  DATA 24
const3_5:  DATA 3
const17_7:  DATA 17
const34_9:  DATA 34
const4_10:  DATA 4
const14_13:  DATA 14
const21_14:  DATA 21
const5_16:  DATA 5
