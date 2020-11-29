import json
with open("dlrobot_human.json", "r") as inp:
    js = json.load(inp)
domains = list()
for domain in js:
    cnt = 0
    for f in js[domain].values():
        if f['intersection_status'] == 'only_human':
            cnt += 1
    if cnt > 10:
        domains.append((cnt, domain))
domains.sort(reverse=True)
for c, d in domains:
    print("{}\t{}".format(d, c))