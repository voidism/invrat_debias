import sys
import csv

c = list(csv.reader(open(sys.argv[2])))

preds = list(csv.reader(open(sys.argv[1])))
c[0].append('invariant')
c[0].append('variant')
print(len(preds))
for i in range(1, len(c)):
    pred = preds[i-1][0].split('\t')
    c[i].append(pred[1])
    c[i].append(pred[2])

w = csv.writer(open(sys.argv[3], 'w'))
for i in c:
    w.writerow(i)
