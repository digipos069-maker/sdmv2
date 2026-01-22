import json
import re

try:
    with open('debug_dramabox_source.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if match:
        json_str = match.group(1)
        data = json.loads(json_str)
        print("Successfully parsed __NEXT_DATA__")
        
        def find_tokens(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ['token', 'accessToken', 'auth', 'authorization'] or (isinstance(v, str) and len(v) > 20 and not ' ' in v and not 'http' in v):
                        # print(f"Potential Token: {k} = {v}")
                        pass
                    if isinstance(v, (dict, list)):
                        find_tokens(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    find_tokens(v, f"{path}[{i}]")

        find_tokens(data)
        
        # Check specific props
        props = data.get('props', {})
        pageProps = props.get('pageProps', {})
        # print(json.dumps(pageProps, indent=2)[:1000])

    else:
        print("__NEXT_DATA__ not found")

except Exception as e:
    print(f"Error: {e}")
