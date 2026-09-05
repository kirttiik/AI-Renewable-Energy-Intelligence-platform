import requests
import re
import json
import urllib3
urllib3.disable_warnings()

r = requests.get('https://www.iexindia.com/market-data/day-ahead-market/market-snapshot', verify=False)
match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
if match:
    data = json.loads(match.group(1))
    print('NEXT DATA FOUND:', bool(data))
    print(str(data)[:2000])
else:
    print('NEXT DATA NOT FOUND')
