import numpy as np

a = [[0,1,2,3,4,5], [0,1,2,3,4,5]]
b = [[6,7,8,9], [6,7,8,9]]
c = [[10,11], [10,11]]
print(np.hstack((a, b, c)))

q = [1, 2, 3, 4]
print(tuple(q))