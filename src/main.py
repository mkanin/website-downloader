import os
import sys
import uuid
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) ' \
             'AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/50.0.2661.102 Safari/537.36'
headers = {'User-Agent': user_agent}


links = set()


def create_initial_dir(start_time_str, url):
    parsed = urlparse(url)
    domain = parsed.netloc
    dir_full_path = os.path.join('sites', start_time_str, domain)
    if not os.path.exists(dir_full_path):
        os.makedirs(dir_full_path)
    return dir_full_path


def save_content(dir_full_path, current_url, response=None):
    parsed = urlparse(current_url)
    path = parsed.path
    head, tail = os.path.split(path)
    if head and head[0] == '/':
        head = head[1:]
    dir_full_path = os.path.join(dir_full_path, head)
    if not os.path.exists(dir_full_path):
        os.makedirs(dir_full_path)
    filename = os.path.join(dir_full_path, tail)
    if not os.path.exists(filename):
        if not response:
            try:
                response = requests.get(current_url, headers=headers)
            except Exception:
                return
        open(filename, 'wb').write(response.content)


def save_html(dir_full_path, current_url, response, soup):
    parsed = urlparse(current_url)
    path = parsed.path
    _, file_extension = os.path.splitext(path)
    head, tail = os.path.split(path)
    if head and head[0] == '/':
        head = head[1:]
    if file_extension.find('.htm') == -1:
        tail = 'index.html'
    local_dir_full_path = os.path.join(dir_full_path, head)
    if not os.path.exists(local_dir_full_path):
        os.makedirs(local_dir_full_path)
    filename = os.path.join(local_dir_full_path, tail)
    if not os.path.exists(filename):
        open(filename, 'w').write(str(soup))
    for script in soup.find_all("script"):
        if script.attrs.get("src"):
            script_url = urljoin(current_url, script.attrs.get("src"))
            links.add(script_url)
            save_content(dir_full_path, script_url)
    for css in soup.find_all("link"):
        if css.attrs.get("href"):
            css_url = urljoin(current_url, css.attrs.get("href"))
            if css_url and css_url[0:4] != 'http':
                continue
            links.add(css_url)
            save_content(dir_full_path, css_url)
    for img in soup.find_all("img"):
        if img.attrs.get("src"):
            img_url = urljoin(current_url, img.attrs.get("src"))
            links.add(img_url)
            save_content(dir_full_path, img_url)


def crawl(dir_full_path, start_url):
    s = [start_url]
    robots_url = urljoin(start_url, 'robots.txt')
    s.append(robots_url)
    explored_urls = set()
    while len(s) > 0:
        current_url = s.pop()
        if current_url not in explored_urls:
            links.add(current_url)
            explored_urls.add(current_url)
            print("Exploring URL {}".format(current_url))
            if current_url and current_url[0:4] != 'http':
                continue
            try:
                response = requests.get(current_url, headers=headers)
            except Exception:
                continue
            if response.status_code not in [200, 201, 301, 302]:
                continue
            content_type = response.headers['Content-Type']
            if content_type.find('text/html') == -1:
                save_content(dir_full_path, current_url, response)
            else:
                soup = BeautifulSoup(response.content, 'html.parser')
                save_html(dir_full_path, current_url, response, soup)
                anchors = soup('a')
                for anchor in reversed(anchors):
                    if 'href' in dict(anchor.attrs):
                        link = anchor['href']
                        local_url = urljoin(current_url, link)
                        links.add(local_url)
                        local_url = local_url.split('#')[0]
                        if (
                                local_url.find(start_url) != -1 and
                                local_url not in explored_urls
                        ):
                            s.append(local_url)


def write_links_file(dir_full_path, start_url):
    parsed = urlparse(start_url)
    path = parsed.path
    head, tail = os.path.split(path)
    if head[0] == '/':
        head = head[1:]
    dir_full_path = os.path.join(dir_full_path, head)
    links_str = '\n'.join(links)
    links_str += '\n'
    id = uuid.uuid1()
    rel_filename = '{id_hex}_links.txt'.format(id_hex=id.hex)
    filename = os.path.join(dir_full_path, rel_filename)
    open(filename, 'w').write(links_str)


def create_full_url(url):
    if url[0:4] != 'http':
        url = 'http://' + url
    if url[-1] != '/':
        url += '/'
    return url


def main():
    if len(sys.argv) < 2:
        return
    start_url = sys.argv[-1]
    start_url = create_full_url(start_url)
    now = datetime.now()
    start_time_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    create_initial_dir(start_time_str, start_url)
    dir_full_path = create_initial_dir(start_time_str, start_url)
    crawl(dir_full_path, start_url)
    write_links_file(dir_full_path, start_url)


if __name__ == '__main__':
    main()
