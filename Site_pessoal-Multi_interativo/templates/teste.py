import requests
resposta=requests.get('https://api.npoint.io/911d19d520d28bb02cd5')
data=resposta.json()
print(data[1]['id'])