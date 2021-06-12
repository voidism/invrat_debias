import sys
import csv

c = list(csv.reader(open(sys.argv[2])))

preds = open(sys.argv[1]).read().split('\n')
c[0].append(sys.argv[3])
for i in range(1, len(c)):
    c[i].append(preds[i-1])

w = csv.writer(open(sys.argv[4], 'w'))
for i in c:
    w.writerow(i)
