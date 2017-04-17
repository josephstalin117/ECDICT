#! /usr/bin/env python
# -*- coding: utf-8 -*-
#======================================================================
#
# dictutils.py - 
#
# Created by skywind on 2017/03/31
# Last change: 2017/03/31 22:20:13
#
#======================================================================
import sys
import os
import time
import stardict
import codecs


#----------------------------------------------------------------------
# python3 compatible
#----------------------------------------------------------------------
if sys.version_info[0] >= 3:
	unicode = str
	long = int
	xrange = range


#----------------------------------------------------------------------
# Word Generator
#----------------------------------------------------------------------
class Generator (object):

	def __init__ (self):
		terms = {}
		terms['zk'] = u'中'
		terms['gk'] = u'高'
		terms['ky'] = u'研'
		terms['cet4'] = u'四'
		terms['cet6'] = u'六'
		terms['toefl'] = u'托'
		terms['ielts'] = u'雅'
		terms['gre'] = u'宝'
		self._terms = terms
		names = ('zk', 'gk', 'ky', 'cet4', 'cet6', 'toefl', 'ielts', 'gre')
		self._term_name = names

	def word_tag (self, data):
		tag = data.get('tag', '')
		text = ''
		for term in self._term_name:
			if not tag:
				continue
			if not term in tag:
				continue
			text += self._terms[term]
		frq = data.get('frq')
		if isinstance(frq, str) or isinstance(frq, unicode):
			if frq in ('', '0'):
				frq = None
		if not frq:
			frq = '-'
		bnc = data.get('bnc')
		if isinstance(bnc, str) or isinstance(bnc, unicode):
			if bnc in ('', '0'):
				bnc = None
		if not bnc:
			bnc = '-'
		if bnc != '-' or frq != '-':
			text += ' %s/%s'%(frq, bnc)
		return text.strip()

	def word_level (self, data):
		head = ''
		collins = data.get('collins', '')
		if isinstance(collins, str) or isinstance(collins, unicode):
			if collins in ('', '0'):
				collins = None
		if collins:
			head = str(collins)
		if data.get('oxford'):
			head = 'K' + head
		return head.strip()

	def word_exchange (self, data):
		if not data:
			return ''
		exchange = data.get('exchange')
		exchange = stardict.tools.exchange_loads(exchange)
		if not exchange:
			return ''
		part = []
		last = ''
		for k, v in stardict.tools._exchanges:
			p = exchange.get(k)
			if p and p != last:
				part.append(u'%s'%p)
				last = p
		if len(part) < 2:
			return ''
		return ', '.join(part)

	def text2html (self, text):
		import cgi
		return cgi.escape(text, True).replace('\n', '<br>')

	# 导出星际译王的词典源文件，用于 DictEditor 转换
	def compile_stardict (self, dictionary, filename, title):
		print('generating ...')
		words = stardict.tools.dump_map(dictionary, False)
		out = {}
		pc = stardict.tools.progress(len(words))
		for word in words:
			pc.next()
			data = dictionary[word]
			phonetic = data['phonetic']
			translation = data['translation']
			if not translation:
				translation = data['definition']
			if not translation:
				print('missing: %s'%word)
				continue
			head = self.word_level(data)
			tag = self.word_tag(data)
			if phonetic:
				if head:
					text = '*[' + phonetic + ']   -' + head + '\n'
				else:
					text = '*[' + phonetic + ']\n'
			elif head:
				text = '-' + head + '\n'
			else:
				text = ''
			text = text + translation
			exchange = self.word_exchange(data)
			if exchange:
				exchange = exchange.replace('\\', '').replace('\n', '')
				text = text + '\n\n' + u'[时态] ' + exchange + ''
			if tag:
				text = text + '\n' + '(' + tag + ')'
			out[word] = text
		pc.done()
		print('saving ...')
		stardict.tools.export_stardict(out, filename, title)
		return pc.count

	# 导出 Mdx 源文件，然后可以用 MdxBuilder 转换成 .mdx词典
	def compile_mdx (self, dictionary, filename, mode = None):
		words = stardict.tools.dump_map(dictionary, False)
		fp = codecs.open(filename, 'w', 'utf-8')
		text2html = self.text2html
		pc = stardict.tools.progress(len(words))
		if mode is None:
			mode = ('name', 'phonetic')
		count = 0
		for word in words:
			pc.next()
			data = dictionary[word]
			phonetic = data['phonetic']
			translation = data['translation']
			if not translation:
				translation = data['definition']
			if not translation:
				continue
			head = self.word_level(data)
			tag = self.word_tag(data)
			fp.write(word.replace('\r', '').replace('\n', '') + '\r\n')
			if 'name' in mode:
				fp.write('<b style="font-size:200%%;">%s'%text2html(word))
				fp.write('</b><br><br>\r\n')
			if 'phonetic' in mode:
				if phonetic or head:
					if phonetic:
						fp.write('<font color=dodgerblue>')
						fp.write(text2html(u'[%s]'%phonetic))
						fp.write('</font>')
					if head:
						if phonetic:
							fp.write(' ')
						fp.write('<font color=gray>')
						fp.write(text2html(u'-%s'%head))
						fp.write('</font>')
					fp.write('<br><br>\r\n')
			for line in translation.split('\n'):
				line = line.rstrip('\r\n ')
				fp.write(text2html(line) + ' <br>\r\n')
			if (not 'phonetic' in mode) and head:
				if tag:
					tag = tag + ' -' + head
				else:
					tag = '-' + head
			exchange = self.word_exchange(data)
			if exchange:
				fp.write('<br><font color=gray>')
				fp.write(u'时态: ' + text2html(exchange) + '</font>\r\n')
			if tag:
				fp.write('<br><font color=gray>')
				fp.write('(%s)'%text2html(tag))
				fp.write('</font>\r\n')
			fp.write('</>')
			if count < len(words) - 1:
				fp.write('\r\n')
			count += 1
		pc.done()
		return pc.count


#----------------------------------------------------------------------
# LazyRequests
#----------------------------------------------------------------------
class LazyRequests (object):
	
	def __init__ (self):
		import threading
		self._pools = {}
		self._lock = threading.Lock()
		self._options = {}
		self._option = {}
	
	def __session_get (self, name):
		hr = None
		with self._lock:
			pset = self._pools.get(name, None)
			if pset:
				hr = pset.pop()
		return hr
	
	def __session_put (self, name, obj):
		with self._lock:
			pset = self._pools.get(name, None)
			if pset is None:
				pset = set()
				self._pools[name] = pset
			pset.add(obj)
		return True

	def request (self, name, url, data = None, post = False, header = None):
		import requests
		s = self.__session_get(name)
		if not s:
			s = requests.Session()
		r = None
		option = self._options.get(name, {})
		argv = {}
		if header is not None:
			argv['headers'] = header
		timeout = self._option.get('timeout', None)
		proxy = self._option.get('proxy', None)
		if 'timeout' in option:
			timeout = option.get('timeout')
		if 'proxy' in option:
			proxy = option['proxy']
		if timeout:
			argv['timeout'] = timeout
		if proxy:
			argv['proxies'] = proxy
		if not post:
			if data is not None:
				argv['params'] = data
		else:
			if data is not None:
				argv['data'] = data
		exception = None
		try:
			if not post:
				r = s.get(url, **argv)
			else:
				r = s.post(url, **argv)
		except requests.exceptions.ConnectionError:
			r = None
		except requests.exceptions.ProxyError:
			r = None
		except requests.exceptions.ConnectTimeout:
			r = None
		except requests.exceptions.RetryError as e:
			r = requests.Response()
			r.status_code = -1
			r.text = 'RetryError'
			r.error = e
		except requests.exceptions.BaseHTTPError:
			r = requests.Response()
			r.status_code = -2
			r.text = 'BaseHTTPError'
			r.error = e
		except requests.exceptions.HTTPError as e:
			r = requests.Response()
			r.status_code = -3
			r.text = 'HTTPError'
			r.error = e
		except requests.exceptions.RequestException as e:
			r = requests.Response()
			r.status_code = -4
			r.error = e
		self.__session_put(name, s)
		return r

	def option (self, name, opt, value):
		if name is None:
			self._option[opt] = value
		else:
			if not name in self._options:
				self._options[name] = {}
			opts = self._options[name]
			opts[opt] = value
		return True

	def get (self, name, url, data = None, header = None):
		return self.request(name, url, data, False, header)

	def post (self, name, url, data = None, header = None):
		return self.request(name, url, data, True, header)


#----------------------------------------------------------------------
# online dictionary
#----------------------------------------------------------------------
class OnlineDictionary (object):

	def __init__ (self):
		self.http = LazyRequests()
		self.http.option(None, 'timeout', 15)
		self.google_translator = None
		self.urban_dictionary = None
		self.request_session = None
		self.youdao_index = 0
		self.sequence = ['bing', 'ciba', 'youdao', 'haici']
		self.ciba_key = ''
	
	def session (self):
		if not self.request_session:
			import requests
			self.request_session = requests.Session()
		return self.request_session

	def request (self, name, url, data = None, post = False, header = None):
		r = self.http.request(name, url, data, post, header)
		if r is None:
			return -1, None
		if r.content:
			text = r.content.decode('utf-8')
		else:
			text = r.text
		return r.status_code, text

	def google (self, word):
		if not self.google_translator:
			from googletranslate import Translator
			p = ['translate.google.com']
			self.google_translator = Translator(service_urls = p)
		translator = self.google_translator
		try:
			x = translator.translate(word, src='en', dest='zh-CN')
		except:
			try:
				x = translator.translate(word, src='en', dest='zh-CN')
			except:
				return None
		if not x:
			return None
		text = x.text
		if text == word:
			return None
		return (word, None, text, None)

	def urban (self, word):
		import urbandictionary
		defs = urbandictionary.define(word)
		if not defs:
			return None
		definition = defs[0].definition
		example = defs[0].example
		if example:
			definition += '\n'
			for line in example.split('\n'):
				line = line.rstrip('\r\n\t ')
				if not line:
					continue
				definition += '> ' + line + '\n'
		return (word, None, None, definition)

	def _bing_extract (self, html):
		from bs4 import BeautifulSoup
		p1 = html.find('<div class="hd_div" id="headword">')
		if p1 < 0:
			return None
		html = html[p1:]
		bs = BeautifulSoup(html, 'lxml')
		obj = {}
		head = bs.find('div', class_ = 'hd_div')
		obj['word'] = unicode(head.text.strip('\r\n\t '))
		pron = bs.find('div', class_ = 'hd_pr')
		if pron:
			text = unicode(pron.text).strip('\r\n\t ')
			p1 = text.find('[')
			if p1 >= 0:
				p2 = text.find(']', p1)
				if p2 >= 0:
					text = text[p1+1:p2]
			if text == u'\u82f1\xa0':
				text = None
			obj['phonetic'] = text
		else:
			obj['phonetic'] = None
		lines = []
		for li in bs.ul.contents:
			if li.name == 'li':
				text = ''
				pos = li.find('span', class_ = 'pos')
				if pos:
					pos = pos.text.strip('\r\n\t ')
					if pos == u'网络':
						pos = u'[网络]'
					text = pos + ' '
				text += li.find('span', class_ = 'def').text.strip('\r\n\t ')
				lines.append(text)
		return obj['word'], obj['phonetic'], '\n'.join(lines)

	def bing (self, word):
		url = 'http://cn.bing.com/dict/search'
		data = {}
		data['intlF'] = 0
		data['q'] = word
		try:
			self._url_quote(word)
		except:
			return None
		code, html = self.request('bing', url, data, False)
		if code != 200:
			print html
			return None
		data = None
		try:
			data = self._bing_extract(html)
		except:
			data = None
		if data is None:
			return None
		return data[0], data[1], data[2], None

	def _youdao_api_request (self, word, user, passwd):
		req = {}
		req['keyfrom'] = user
		req['key'] = passwd
		req['type'] = 'data'
		req['doctype'] = 'json'
		req['version'] = '1.1'
		req['q'] = word
		url = 'http://fanyi.youdao.com/openapi.do'
		code, data = self.request('youdao', url, req, True)
		if code != 200:
			print('youdao: http %d'%code)
			return None
		import json
		try:
			obj = json.loads(data)
		except:
			print('youdao: json error')
			return 0
		obj['error'] = 0
		obj['message'] = 'ok'
		return obj

	def _youdao_api_auto (self, word):
		count = 0
		while self.youdao_keys:
			user, passwd = self.youdao_keys[-1]
			if count:
				print('youdao switch key to %s'%user)
			data = self._youdao_api_request(word, user, passwd)
			retry = False
			if data is None:
				return None
			elif data is 0:
				retry = True
			elif 'errorCode' in data:
				if data['errorCode'] == 50:
					retry = True
			if not retry:
				return data
			self.youdao_keys.pop()
			count += 1
		return 0

	def youdao_api (self, word):
		data = self._youdao_api_auto(word)
		if data is None:
			return None
		if data is 0:
			return 0
		if not 'basic' in data:
			return None
		key = word
		phonetic = None
		explain = None
		translation = None
		if 'web' in data:
			for web in data['web']:
				if not 'key' in web:
					continue
				if word == web['key']:
					key = web['key']
					break
			if not key:
				for web in data['web']:
					if not 'key' in web:
						continue
					if word.lower() == web['key'].lower():
						key = web['key']
						break
		basic = data['basic']
		if 'phonetic' in basic:
			phonetic = basic['phonetic']
		elif 'phonetic_uk' in basic:
			phonetic = basic['phonetic_uk']
		elif 'phonetic_us' in basic:
			phonetic = basic['phonetic_us']
		if 'explains' in basic:
			explain = '\n'.join(basic['explains'])
		translation = data.get('translation')
		return key, phonetic, explain, None

	def _iciba_api_query (self, word):
		url = 'http://dict-co.iciba.com/api/dictionary.php'
		req = {}
		req['w'] = word
		req['type'] = 'json'
		req['key'] = self.ciba_key
		code, data = self.request('ciba', url, req, False)
		if code != 200:
			return None
		import json
		try: 
			body = json.loads(data)
		except:
			print('ciba json error')
			return 0
		return body

	def ciba_api (self, word):
		req = self._iciba_api_query(word)
		if req is None:
			return None
		if req is 0:
			return 0
		name = req.get('word_name', None)
		if not name:
			return None
		symbols = req.get('symbols')
		if not symbols:
			return 0
		if not isinstance(symbols, list):
			return 0
		symbol = symbols[0]
		if symbol.get('ph_en'):
			phonetic = symbol['ph_en']
		elif symbol.get('ph_am'):
			phonetic = symbol['ph_am']
		elif symbol.get('ph_other'):
			phonetic = symbol['ph_other']
		else:
			phonetic = None
		parts = symbol.get('parts', [])
		output = []
		for part in parts:
			text = part['part'] + ' ' + '; '.join(part['means'])
			output.append(text)
		translation = '\n'.join(output)
		if phonetic:
			mark = 'http://res-tts.iciba.com'
			size = len(mark)
			if phonetic[:size] == mark:
				phonetic = phonetic[size:]
		return name, phonetic, translation, ''

	def _soup_text (self, text):
		# break into lines and remove leading and trailing space on each
		lines = (line.strip() for line in text.splitlines())
		# break multi-headlines into a line each
		chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
		# drop blank lines
		text = '\n'.join(chunk for chunk in chunks if chunk)
		return text

	def _youdao_extract (self, html, engine = None):
		from bs4 import BeautifulSoup 
		if not html:
			return None
		if not engine:
			soup = BeautifulSoup(html)
		else:
			soup = BeautifulSoup(html, engine)
		data = {}
		listtab = soup.find('div', class_ = 'trans-wrapper')
		if not listtab:
			return None
		keyword = listtab.find('span', class_ = 'keyword')
		if keyword:
			data['word'] = unicode(keyword.text).strip('\r\n\ ')
		phonetic = listtab.find('span', class_ = 'phonetic')
		if phonetic:
			phonetic = unicode(phonetic.text).strip('\r\n\t ')
			if phonetic[:1] == '[' and phonetic[-1:] == ']':
				phonetic = phonetic[1:-1]
			data['phonetic'] = phonetic
		trans = listtab.find('div', class_ = 'trans-container')
		if not trans:
			return None
		translation = unicode(trans.text).strip('\r\n\t ')
		data['translation'] = self._soup_text(translation)
		return data

	def _url_quote (self, text):
		if sys.version_info[0] < 3:
			import urllib
			return urllib.quote(text)
		else:
			import urllib.parse
			return urllib.parse.quote(text)
		return ''

	def youdao_web (self, word):
		word = word.strip('\r\n\t ')
		if not word:
			return None
		try:
			url = 'http://www.youdao.com/w/' + self._url_quote(word)
		except:
			return None
		code, html = self.request('youdao2', url)
		if code != 200:
			return None
		data = self._youdao_extract(html, 'lxml')
		if not data:
			return None
		if 'word' in data:
			word = data['word']
		phonetic = data.get('phonetic', None)
		translation = data.get('translation', None)
		return word, phonetic, translation, None

	def _haici_extract (self, html, engine = None):
		from bs4 import BeautifulSoup
		html = html.strip('\r\n\t ')
		if not html:
			return None
		if engine is None:
			soup = BeautifulSoup(html)
		else:
			soup = BeautifulSoup(html, engine)
		content = soup.find('div', id = 'content')
		if not content:
			return None
		[s.extract() for s in soup('script')]
		data = {}
		if content.h1:
			data['word'] = unicode(content.h1.text).strip('\r\n\t ')
		bdo = content.bdo
		if bdo:
			text = unicode(bdo.text).strip('\r\n\t ')
			if text[:1] == '[' and text[-1:] == ']':
				text = text[1:-1]
			data['phonetic'] = text
		ul = content.find('ul', class_ = 'dict-basic-ul')
		if ul is None:
			return None
		lines = []
		for tag in ul.contents:
			if tag.name != 'li':
				continue
			text = unicode(tag.text.replace('\n', ' '))
			lines.append(text.strip('\r\n\t '))
		text = '\n'.join(lines)
		data['translation'] = text.rstrip('\r\n\t ')
		# print text.encode('gbk', 'ignore')
		# print html.encode('gbk', 'ignore')
		chart = content.find('div', class_ = 'dict-chart')
		if chart:
			chart = chart.get('data')
			if sys.version_info[0] < 3:
				import urllib
				chart = urllib.unquote(chart)
			else:
				import urllib.parse
				chart = urllib.parse.unquote(chart)
			import json
			decode = None
			try: decode = json.loads(chart)
			except: pass
			if decode:
				data['chart'] = decode
		return data

	def haici (self, word):
		word = word.strip('\r\n\t ')
		if not word:
			return None
		try:
			url = 'http://dict.cn/' + self._url_quote(word)
		except:
			return None
		code, html = self.request('haici', url)
		if code != 200:
			return None
		data = self._haici_extract(html, 'lxml')
		if not data:
			return None
		word = data.get('word', word)
		phonetic = data.get('phonetic', None)
		translation = data.get('translation', None)
		if not translation:
			return None
		chart = data.get('chart', None)
		return word, phonetic, translation, chart

	def comprehensive (self, word):
		word = word.strip('\r\n\t ')
		if not word:
			return None
		for seq in self.sequence:
			if seq == 'bing':
				data = self.bing(word)
				if data:
					return data[0], data[1], data[2], 'bing'
			elif seq == 'ciba':
				if self.ciba_key:
					data = self.ciba_api(word)
					if data:
						return data[0], data[1], data[2], 'ciba'
			elif seq == 'youdao':
				if self.youdao_keys:
					data = self.youdao_api(word)
					if data:
						return data[0], data[1], data[2], 'youdao_api'
					if data is 0:
						data = self.youdao_web(word)
					if data:
						return data[0], data[1], data[2], 'youdao'
				else:
					data = self.youdao_web(word)
				if data:
					return data[0], data[1], data[2], 'youdao'
			elif seq == 'haici':
				data = self.haici(word)
				if data:
					return data[0], data[1], data[2], 'haici'
		return None


#----------------------------------------------------------------------
# generation
#----------------------------------------------------------------------
generator = Generator()
online = OnlineDictionary()


#----------------------------------------------------------------------
# KEYS
#----------------------------------------------------------------------
YOUDAO_KEYS = [
	 ('YouDaoCV', '659600698'),
	 ('11pegasus11', '273646050'),
	 ('longcwang', '131895274'),
	 ('wufeifei', '716426270'),
	 ('tinxing', '1312427901'),
	 ('cctv10', '1365682047'),
	 ('YoungdzeBlog', '498418215'),
	 ('HaloWordDictionary', '1311342268'),
	 ('chinacache', '1247577973'),
	 ('chendihao', '707664099'),
	 ('huipblog', '439918742'),
	 ('github-wdict', '619541059'),
	 ('wolang', '782273338'),
	 ('goodDic', '2121816595'),
	 ('ice-blog-home', '1274584216'),
	 ('zhouyunongBlog', '2039183788'),
	 ('orchid', '1008797533'),
	 ('yichaci', '1180520206'),
	 ('dragonqian', '607489832'),
	 ('learn-english-cfw', '711979406'),
	 ('Nino-Tips', '1127122345'),
	 ('whyliam', '1331254833'),
	 ('whyliam-wf-1', '2002493135'),
	 ('whyliam-wf-2', '2002493136'),
	 ('whyliam-wf-3', '2002493137'),
	 ('whyliam-wf-4', '2002493138'),
	 ('whyliam-wf-5', '2002493139'),
	 ('whyliam-wf-6', '2002493140'),
	 ('whyliam-wf-7', '2002493141'),
	 ('whyliam-wf-8', '2002493142'),
	 ('whyliam-wf-9', '2002493143'),
	 ('whyliam-wf-10', '1947745089'),
	 ('whyliam-wf-11', '1947745090')
	 ]

online.youdao_keys = YOUDAO_KEYS
online.ciba_key = '9DA88066B55AAE05257E0E5AF6343B90'


#----------------------------------------------------------------------
# testing case
#----------------------------------------------------------------------
if __name__ == '__main__':
	def test1():
		print online.bing('economy-wide')
		PROXY = 'socks5://192.168.0.23:1080'
		PROXY = 'socks5://192.168.1.2:1080'
		os.environ['HTTP_PROXY'] = PROXY
		os.environ['HTTPS_PROXY'] = PROXY
		print online.google('hello')
		return 0
	def test2():
		s = online.session()
		r = s.get('http://vn1.skywind.me:8080/gold/echo', params = {'x':1})
		print r.text
	def test3():
		lr = LazyRequests()
		t0 = time.time()
		for i in xrange(10):
			t = time.time()
			r = lr.request('fuck' + str(0), 'http://vn1.skywind.me:8080/gold/echo', {'y':2}, True)
			print time.time() - t
		print r.text
		print time.time() - t0
	def test4():
		print online.youdao_api('kiss8ulksjdfoiiuq')
		print online.youdao_web('kiss')
		print online.haici('english')
		print online.bing('accrete')
		# data = online.ciba_api('kiss')
	def test5():
		# online.sequence = ['youdao', 'ciba', 'bing']
		data = online.comprehensive('veluot')[2].encode('gbk', 'ignore')
		print data
		print online.comprehensive('realestate')

	test4()



