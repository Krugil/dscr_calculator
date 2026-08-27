import math
P=200000
r=0.05/12
n=240
payment=P*r/(1-math.pow(1+r,-n))
print(payment)
print(7000/payment)
