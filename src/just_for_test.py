import requests
from bs4 import BeautifulSoup

url = "http://www.cs.vsu.ru/~svv/style/styles.css"

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) ' \
             'AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/50.0.2661.102 Safari/537.36'
headers = {'User-Agent': user_agent}

response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.content, 'html.parser')

urls = []

start_pos = 0
offset = 4
while str(soup).find('url', start_pos) != -1:
    start_pos = str(soup).find('url', start_pos)
    start_pos += offset
    end_pos = str(soup).find(')', start_pos)
    url = str(soup)[start_pos:end_pos]
    urls.append(url)
    start_pos = end_pos

result_str = '\n'.join(urls)

print(result_str)
