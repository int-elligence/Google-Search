import requests
import time
import urllib
import multiprocessing, threading
import random
from BeautifulSoup import BeautifulSoup

USER_AGENTS = {
	"firefox": [
	    "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0",
	    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0",
	    "Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0",
	],
	"safari": [
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/534.55.3 (KHTML, like Gecko) Version/5.1.3 Safari/534.53.10",
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
	],
	"ie": [
		"Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko",
		"Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)",
		"Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)",
	],
}

class ResultPage(BeautifulSoup):
	def __init__(self, html):
		super(ResultPage, self).__init__(html)
		self.html = html
	def find_next_page_link(self):
		return 'https://www.google.com{}'.format(self.findAll('div',attrs={'id':'navcnt'})[0].findAll('a')[0]['href'])
	def find_result_links(self):
		result_links = []
		result_divs = self.findAll('div', attrs={'class':'rc'})
		for result_div in result_divs:
			result_links.append(result_div.findAll('a')[0]['href'])
		return result_links

class SearchTask(object):
	def __init__(self, query, pages):
		super(SearchTask, self).__init__()
		self.cookies = self.get_cookies()
		self.query = query
		self.pages = pages
		self.user_agent = random.choice(USER_AGENTS[random.choice(USER_AGENTS.keys())])
		self.headers = {'User-Agent':self.user_agent, 'DNT': '1'}
		self.init_url = 'https://www.google.com/search?rls=en&q={}&ie=UTF-8&oe=UTF-8'.format(self.query)
	def get_cookies(self):
		return requests.get('https://www.google.com/').cookies
	def __call__(self):
		result_urls = []
		time.sleep(random.randint(1,1000)/1000.0)
		initial_resp = requests.get(self.init_url, headers=self.headers, cookies=self.cookies)
		initial_html = initial_resp.text
		initial_result_page = ResultPage(initial_html)
		initial_result_links = initial_result_page.find_result_links()
		for result_link in initial_result_links:
			result_urls.append(result_link)
		result_page = initial_result_page
		for i in xrange(1, self.pages):
			next_url = result_page.find_next_page_link()
			time.sleep(random.randint(1,1000)/1000.0)
			resp = requests.get(next_url, headers=self.headers, cookies=self.cookies)
			html = resp.text
			result_page = ResultPage(html)
			result_links = result_page.find_result_links()
			result_urls += result_links
		return result_urls

class ScanEngine(object):
	def __init__(self, pool_size=1):
		super(ScanEngine, self).__init__()
		self.finished = False
		self.thread_pool = multiprocessing.Pool(pool_size)
		self.result_urls = []
		self.search_tasks = []
	def add_search_task(self, search_task):
		self.search_tasks.append(search_task)
	def run(self):
		threads = []
		for task in self.search_tasks:
			self.thread_pool.apply_async(task, callback=self.result_urls.extend)
		self.thread_pool.close()
		self.thread_pool.join()
		self.finished = True
		return self.result_urls

class GoogleSearcher(object):
	def __init__(self, pool_size=1):
		super(GoogleSearcher, self).__init__()
		self.pool_size = pool_size
		self.scan_engine = ScanEngine(pool_size=self.pool_size)
	def do_searches_from_file(self, filename, pages_per_search=1):
		if self.scan_engine.finished:
			self.scan_engine = ScanEngine(pool_size=self.pool_size)
		with open(filename, 'r') as f:
			search_queries = f.read().replace('\r','')
			while '\n\n' in search_queries:
				search_queries = search_queries.replace('\n\n', '\n')
			search_queries = search_queries.split('\n')
			for search_query in search_queries:
				self.scan_engine.add_search_task(SearchTask(search_query, pages_per_search))
		return self.scan_engine.run()
	def do_single_search(self, search_query, pages_per_search=1):
		if self.scan_engine.finished:
			self.scan_engine = ScanEngine(pool_size=self.pool_size)
		self.scan_engine.add_search_task(SearchTask(search_query, pages_per_search))
		return self.scan_engine.run()
