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
# 
#----------------------------------------------------------------------
class OnlineDictionary (object):

	def __init__ (self):
		self.google_translator = None
		self.urban_dictionary = None
	
	def _http_request (self, url, timeout, data, post, head = None):
		headers = []
		import urllib
		import ssl
		if sys.version_info[0] >= 3:
			import urllib.parse
			import urllib.request
			import urllib.error
			if data is not None:
				if isinstance(data, dict):
					data = urllib.parse.urlencode(data)
			if not post:
				if data is None:
					req = urllib.request.Request(url)
				else:
					mark = '?' in url and '&' or '?'
					req = urllib.request.Request(url + mark + data)
			else:
				data = data is not None and data or ''
				if not isinstance(data, bytes):
					data = data.encode('utf-8', 'ignore')
				req = urllib.request.Request(url, data)
			if head:
				for k, v in head:
					req.add_header(k, v)
			try:
				res = urllib.request.urlopen(req, timeout = timeout)
				headers = res.getheaders()
			except urllib.error.HTTPError as e:
				return e.code, str(e.message), None
			except urllib.error.URLError as e:
				return -1, str(e), None
			except socket.timeout:
				return -2, 'timeout', None
			except ssl.SSLError:
				return -2, 'timeout', None
			content = res.read()
		else:
			import urllib2
			if data is not None:
				if isinstance(data, dict):
					part = {}
					for key in data:
						val = data[key]
						if isinstance(key, unicode):
							key = key.encode('utf-8')
						if isinstance(val, unicode):
							val = val.encode('utf-8')
						part[key] = val
					data = urllib.urlencode(part)
				if not isinstance(data, bytes):
					data = data.encode('utf-8', 'ignore')
			if not post:
				if data is None:
					req = urllib2.Request(url)
				else:
					mark = '?' in url and '&' or '?'
					req = urllib2.Request(url + mark + data)
			else:
				req = urllib2.Request(url, data is not None and data or '')
			if head:
				for k, v in head:
					req.add_header(k, v)
			try:
				res = urllib2.urlopen(req, timeout = timeout)
				content = res.read()
				if res.info().headers:
					for line in res.info().headers:
						line = line.rstrip('\r\n\t')
						pos = line.find(':')
						if pos < 0:
							continue
						key = line[:pos].rstrip('\t ')
						val = line[pos + 1:].lstrip('\t ')
						headers.append((key, val))
			except urllib2.HTTPError as e:
				return e.code, str(e.message), None
			except urllib2.URLError as e:
				return -1, str(e), None
			except socket.timeout:
				return -2, 'timeout', None
			except ssl.SSLError:
				return -2, 'timeout', None
		return 200, content, headers

	def request (self, url, data = None, timeout = 15, post = False):
		count = 0
		x = -1, None
		while count < 3:
			head = []
			head.append(('Content-Type', 'text/plain; charset:utf-8;'))
			x = self._http_request(url, timeout, data, post, head)
			code = x[0]
			if x != -2:
				return x[0], x[1]
			count += 1
		return x[0], x[1]

	def google (self, word):
		if not self.google_translator:
			from googletranslate import Translator
			p = ['translate.google.com.hk', 'translate.google.com']
			self.google_translator = Translator()
		translator = self.google_translator
		x = translator.translate(word, src='en', dest='zh-CN')
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
		code, html = self.request(url, data, 20, False)
		if code != 200:
			print html
			return None
		data = None
		try:
			data = self._bing_extract(html)
		except:
			code, html = self.request(url, data, 20, False)
			if code != 200:
				return None
			if 1:
				data = self._bing_extract(html)
			if 0:
				return None
		if data is None:
			return None
		return data[0], data[1], data[2], None




#----------------------------------------------------------------------
# generation
#----------------------------------------------------------------------
generator = Generator()
online = OnlineDictionary()


#----------------------------------------------------------------------
# testing case
#----------------------------------------------------------------------
if __name__ == '__main__':
	def test1():
		print online.bing('hello')
		print online.google('hello')
		return 0

	test1()



