import urllib.request
import json  

userInfo='{"username": "david_parsers", "password": "vMrkq002"}'.encode("ascii")
authUrl = 'https://declarator.org/api/api-token-auth/'
req = urllib.request.Request(authUrl, data=userInfo,
                             headers={'content-type': 'application/json'})
res = urllib.request.urlopen(req) 
token = json.loads(res.read())['token']


patternUrl='https://declarator.org/api/patterns'
allPatterns = []
while patternUrl != "" and patternUrl is not None:
    req = urllib.request.Request(patternUrl, headers={'content-type': 'application/json'})
    res = urllib.request.urlopen(req) 
    page = json.loads(res.read())
    allPatterns += page['results']
    patternUrl = page.get('next', "")


with open("patterns.json", "w", encoding="utf8") as outf:
    json.dump({"results":allPatterns}, outf, indent=4, ensure_ascii=False)
    

