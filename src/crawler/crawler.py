import os
from urllib.parse import urljoin, urlparse

import requests as requests
from bs4 import BeautifulSoup


class Crawler:

    def __init__(self, headers, dir_full_path, start_url, additional_urls=[]):
        self.headers = headers
        self.dir_full_path = dir_full_path
        self.start_url = start_url
        self.additional_urls = additional_urls
        self.links = []
        self.links_short = []
        self.explored_urls = set()

    def save_content(self, current_url, response=None, mark_as_explored=False):
        parsed = urlparse(current_url)
        path = parsed.path
        head, tail = os.path.split(path)
        if head and head[0] == '/':
            head = head[1:]
        dir_full_path = os.path.join(self.dir_full_path, head)
        if not os.path.exists(dir_full_path):
            os.makedirs(dir_full_path)
        filename = os.path.join(dir_full_path, tail)
        if not os.path.exists(filename):
            if not response:
                try:
                    response = requests.get(current_url, headers=self.headers)
                except Exception:
                    return -1
            if response.status_code not in [200, 201]:
                return -1
            open(filename, 'wb').write(response.content)
            if mark_as_explored:
                self.explored_urls.add(current_url)
            return 0
        return 1

    def strip_url(self, url):
        url = url.strip()
        if url.startswith('\'') and url.endswith('\''):
            url = url.strip('\'')
        elif url.startswith('"') and url.endswith('"'):
            url = url.strip('"')
        return url

    def save_css_with_urls(self, current_url):
        try:
            response = requests.get(current_url, headers=self.headers)
        except Exception:
            return
        res = self.save_content(current_url, response)
        if res == -1:
            return
        soup = BeautifulSoup(response.content, 'html.parser')
        start_pos = 0
        offset = 4
        while str(soup).find('url', start_pos) != -1:
            start_pos = str(soup).find('url', start_pos)
            start_pos += offset
            end_pos = str(soup).find(')', start_pos)
            url = str(soup)[start_pos:end_pos]
            start_pos = end_pos
            url = self.strip_url(url)
            url = urljoin(current_url, url)
            self.links if url in self.links else self.links.append(url)
            if url not in self.explored_urls:
                self.save_content(url, mark_as_explored=True)

    def save_html(self, current_url, response, soup):
        parsed = urlparse(current_url)
        path = parsed.path
        _, file_extension = os.path.splitext(path)
        head, tail = os.path.split(path)
        if head and head[0] == '/':
            head = head[1:]
        if file_extension.find('.htm') == -1:
            tail = 'index.html'
        local_dir_full_path = os.path.join(self.dir_full_path, head)
        if not os.path.exists(local_dir_full_path):
            os.makedirs(local_dir_full_path)
        filename = os.path.join(local_dir_full_path, tail)
        if not os.path.exists(filename):
            open(filename, 'wb').write(response.content)
        for script in soup.find_all("script"):
            if script.attrs.get("src"):
                script_url = urljoin(current_url, script.attrs.get("src"))
                self.links if script_url in self.links else \
                    self.links.append(script_url)
                if script_url not in self.explored_urls:
                    self.save_content(script_url, mark_as_explored=True)
        for css in soup.find_all("link", rel="stylesheet"):
            if css.attrs.get("href"):
                css_url = urljoin(current_url, css.attrs.get("href"))
                if css_url and css_url[0:4] != 'http':
                    continue
                self.links if css_url in self.links else \
                    self.links.append(css_url)
                if css_url not in self.explored_urls:
                    self.save_css_with_urls(css_url)
        for icon in soup.find_all("link", rel="icon"):
            if icon.attrs.get("href"):
                icon_url = urljoin(current_url, icon.attrs.get("href"))
                if icon_url and icon_url[0:4] != 'http':
                    continue
                self.links if icon_url in self.links else \
                    self.links.append(icon_url)
                if icon_url not in self.explored_urls:
                    self.save_content(icon_url, mark_as_explored=True)
        for img in soup.find_all("img"):
            if img.attrs.get("src"):
                img_url = urljoin(current_url, img.attrs.get("src"))
                self.links if img_url in self.links else \
                    self.links.append(img_url)
                if img_url not in self.explored_urls:
                    self.save_content(img_url, mark_as_explored=True)

    def create_path_to_robots_file(self, start_url):
        parsed = urlparse(start_url)
        urn = '{scheme}://{netloc}/'.format(
            scheme=parsed.scheme, netloc=parsed.netloc
        )
        robots_url = urljoin(urn, 'robots.txt')
        return robots_url

    def crawl(self):
        s = []
        robots_url = self.create_path_to_robots_file(self.start_url)
        s.append(robots_url)
        s.append(self.start_url)
        for additional_url in self.additional_urls:
            if (
                    additional_url.find(self.start_url) != -1 and
                    additional_url not in s
            ):
                s.append(additional_url)
        while len(s) > 0:
            current_url = s.pop(0)
            if current_url not in self.explored_urls:
                self.links if current_url in self.links else \
                    self.links.append(current_url)
                self.links_short if current_url in self.links_short \
                    else self.links_short.append(current_url)
                self.explored_urls.add(current_url)
                print("Exploring URL {}".format(current_url))
                if current_url and current_url[0:4] != 'http':
                    continue
                try:
                    response = requests.get(current_url, headers=self.headers)
                except Exception:
                    continue
                if response.status_code not in [200, 201, 301, 302]:
                    continue
                content_type = response.headers.get('Content-Type', '')
                if content_type.find('text/html') == -1:
                    self.save_content(current_url, response)
                else:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    self.save_html(current_url, response, soup)
                    anchors = soup('a')
                    for anchor in anchors:
                        if 'href' in dict(anchor.attrs):
                            link = anchor['href']
                            local_url = urljoin(current_url, link)
                            self.links if local_url in self.links else \
                                self.links.append(local_url)
                            local_url = local_url.split('#')[0]
                            if (
                                    local_url.find(self.start_url) != -1 and
                                    local_url not in self.explored_urls
                            ):
                                s.append(local_url)
