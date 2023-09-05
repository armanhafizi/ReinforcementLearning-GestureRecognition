import numpy as np
modes = ['circle-cw', 'circle-ccw', 'swipe-r', 'swipe-l', 'swipe-u', 'swipe-d', 'swipe-f', 'swipe-b', 'ok', 'stop']
mode = modes[7]
filename = 'data/' + mode + '.npy'
read = np.load(filename, allow_pickle=True)
print(read[0])
# for i in range(len(read)):
#     print(read[i][0])
# main program