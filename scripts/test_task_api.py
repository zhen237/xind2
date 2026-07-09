import urllib.request
import json

url = 'http://localhost:8083/api/m03/design/tasks'
data = {
    'taskName': '测试任务',
    'projectId': 1,
    'paramsJson': '{"centerLongitude":116.4074,"centerLatitude":39.9042,"coverageRadius":500,"templateType":"macro"}'
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    response = urllib.request.urlopen(req)
    result = response.read().decode('utf-8')
    print('Response:', result)
except Exception as e:
    print('Error:', str(e))
    if hasattr(e, 'code'):
        print('Status code:', e.code)
        try:
            print('Error body:', e.read().decode())
        except:
            pass
