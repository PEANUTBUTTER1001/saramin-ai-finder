import urllib.request
import re

try:
    req = urllib.request.Request('https://m.saramin.co.kr/job-search/view?rec_idx=46700000', headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    intents = re.findall(r'intent://[^>\"\'\s]+', html)
    print("Found intents:")
    for intent in intents:
        print(intent)
        
    schemes = re.findall(r'saram[^>\"\'\s]+://[^>\"\'\s]+', html)
    print("\nFound schemes:")
    for scheme in schemes:
        print(scheme)
except Exception as e:
    print("Error:", e)
