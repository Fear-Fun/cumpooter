# Determine the maximum of two integers.
# This program triggers memory-mapped IO to
# read integers from the keyboard and to
# write integers to the display.
   LOAD r1,r0,r0[510]     # Trigger read from console
   LOAD r2,r0,r0[510]     # Trigger read from console
   SUB  r0,r1,r2[0]
   JUMP/P r1bigger
   STORE r2,r0,r0[511]    # Trigger write to console
   HALT r0,r0,r0
r1bigger:
   STORE r1,r0,r0[511]    # Trigger write to console
   HALT r0,r0,r0
   