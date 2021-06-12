import re, sys

word_file = open("word_based_bias_list.csv").readlines()

words = []
for i in word_file[1:]:
    words.append(i.split(',')[0])

f = open(sys.argv[1])
fw = open(sys.argv[2], 'w')
for line in f:
    for word in words:
        gex = re.compile(word)
        find = gex.findall(line)
        if len(find)>0:
            print(find)
        line = re.sub(word, '', line)
    fw.write(line)
