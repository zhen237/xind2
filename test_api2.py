import urllib.request
import urllib.error

try:
    r = urllib.request.urlopen('http://localhost:8085/api/m05/device', timeout=10)
    print('Status:', r.status)
    print('Content:', r.read().decode())
except urllib.error.HTTPError as e:
    print('Status:', e.code)
    print('Reason:', e.reason)
    print('Headers:')
    for key, value in e.headers.items():
        print(f'  {key}: {value}')
    print('Content:', e.read().decode())
except Exception as e:
    print('Error:', str(e))
    import traceback
    traceback.print_exc()
