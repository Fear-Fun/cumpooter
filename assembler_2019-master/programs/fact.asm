# Lovingly crafted by robots
# 2018-05-24 10:13:01.543036 from programs/fact.awl
#
	LOAD r1,r0,r0[510]
	STORE  r1,x_1
	LOAD r1,const1_3  # Const 1
	STORE  r1,fact_2
loop_4:  #While loop
	LOAD r2,x_1
	SUB  r0,r2,r0 
	JUMP/Z endloop_5
	LOAD r1,fact_2
	LOAD r2,x_1
	MUL  r1,r1,r2
	STORE  r1,fact_2
	LOAD r1,x_1
	LOAD r2,const1_3  # Const 1
	SUB  r1,r1,r2
	STORE  r1,x_1
	JUMP loop_4
endloop_5: 
	LOAD r1,fact_2
	STORE  r1,r0,r0[511]
	HALT  r0,r0,r0
x_1: DATA 0 #x
fact_2: DATA 0 #fact
const1_3:  DATA 1
