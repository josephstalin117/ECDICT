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
				fp.write('<b style="font-size:180%%;">%s'%text2html(word))
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

	def list_load (self, filename, encoding = 'utf-8'):
		words = {}
		import codecs
		with codecs.open(filename, encoding = encoding) as fp:
			for line in fp:
				line = line.strip('\r\n\t ')
				if not line:
					continue
				words[line] = 1
		return words

	def list_save (self, filename, words):
		import codecs
		with codecs.open(filename, 'w', encoding = 'utf-8') as fp:
			for w in words:
				fp.write(w + '\n')
		return True



#----------------------------------------------------------------------
# 解析 resemble.txt 生成辨析释义
#----------------------------------------------------------------------
class Resemble (object):

	def __init__ (self):
		self._resembles = []
		self._words = {}
		self._filename = None
		self._lineno = 0

	def error (self, text):
		t = '%s:%s: error: %s\n'
		t = t%(self._filename, self._lineno, text)
		sys.stderr.write(t)
		sys.stderr.flush()
	
	def load (self, filename):
		self._resembles = []
		self._words = {}
		file_content = stardict.tools.load_text(filename)
		if file_content is None:
			sys.stderr.write('cannot read: %s\n'%filename)
			return False
		key = None
		content = []
		self._filename = filename
		self._lineno = 0
		for line in file_content.split('\n'):
			line = line.strip('\r\n\t ')
			self._lineno += 1
			if key is None:
				if not line:
					continue
				if line[:1] != '%':
					self.error('must starts with a percent sign')
					return False
				line = line[1:].lstrip('\r\n\t ')
				key = [ n.strip('\r\n\t ') for n in line.split(',') ]
				if not key:
					self.error('empty heading words')
					return False
				content = []
			else:
				if not line:
					wt = {}
					wt['words'] = tuple(key)
					wt['content'] = content
					self._resembles.append(wt)
					key = None
					content = []
				elif line[:1] == '-':
					line = line[1:].lstrip('\r\n\t')
					pos = line.find(':')
					if pos < 0:
						self.error('expect colon')
					word = line[:pos].strip('\r\n\t ')
					text = line[pos+1:].strip('\r\n\t ')
					text = text.replace('\\n', '\n')
					content.append((word, text))
				else:
					content.append(line)
		if key:
			wt = {'words':tuple(key), 'content':content}
			self._resembles.append(wt)
		self._init_refs()
		return True

	def _init_refs (self):
		self._words = {}
		words = {}
		for wt in self._resembles:
			for word in wt['words']:
				if not word in words:
					words[word] = []
				words[word].append(wt)
		for word in words:
			self._words[word] = tuple(words[word])
		return True

	def __len__ (self):
		return len(self._resembles)

	def __getitem__ (self, key):
		if isinstance(key, int) or isinstance(key, long):
			return self._resembles[key]
		return self._words[key]

	def __contains__ (self, key):
		if isinstance(key, int) or isinstance(key, long):
			if key < 0 or key >= len(self._resembles):
				return False
		elif not key in self._words:
			return False
		return True

	def __iter__ (self):
		return self._resembles.__iter__()

	def text2html (self, text):
		import cgi
		return cgi.escape(text, True).replace('\n', '<br>')

	def dump_text (self, wt):
		lines = []
		lines.append('% ' + (', '.join(wt['words'])))
		for content in wt['content']:
			if isinstance(content, list) or isinstance(content, tuple):
				word, text = content
				text = text.replace('\n', '\\n')
				lines.append('- ' + word + ': ' + text)
			else:
				lines.append(content)
		return '\n'.join(lines)

	def dump_html (self, wt):
		lines = []
		text2html = self.text2html
		lines.append('<div class="discriminate">')
		text = ', '.join(wt['words'])
		text = '<div class="dis-group"><b>' + text2html(text) + '</b></div>'
		lines.append(text)
		lines.append('<div class="dis-content">')
		for content in wt['content']:
			if isinstance(content, tuple) or isinstance(content, list):
				head = content[0]
				desc = content[1]
				text = '<font color="dodgerblue">%s</font>: '%text2html(head)
				text = text + text2html(desc)
				lines.append(text + '<br>')
			else:
				lines.append(text2html(content) + '<br>')
		lines.append('</div>')
		lines.append('</div>')
		return '\n'.join(lines)

	def compile_mdx (self, filename):
		words = {}
		if (not self._resembles) or (not self._words):
			return False
		pc = stardict.tools.progress(len(self._words))
		for word in self._words:
			pc.next()
			wts = [ self.dump_html(wt) for wt in self._words[word] ]
			words[word] = '<br>\n'.join(wts)
		title = u'有道词语辨析'
		text = time.strftime('%Y-%m-%d %H:%M:%S')
		desc = u'<font color="red">\n'
		desc += u'有道词语辨析<br>\n'
		desc += u'词条数：%d<br>\n'%len(self._words)
		desc += u'词组数：%d<br>\n'%len(self._resembles)
		desc += u'作者：skywind<br>\n'
		desc += u'日期：%s<br>\n'%text
		desc += '</font>'
		stardict.tools.export_mdx(words, filename, title, desc)
		pc.done()
		return True



#----------------------------------------------------------------------
# generation
#----------------------------------------------------------------------
generator = Generator()
resemble = Resemble()


#----------------------------------------------------------------------
# testing case
#----------------------------------------------------------------------
if __name__ == '__main__':
	
	def test1():
		print('hello')

	def test2():
		resemble.load('resemble.txt')
		print resemble.dump_text(resemble[0])
		print ''
		return 0

	def test3():
		resemble.load('resemble.txt')
		fn = 'd:/Program Files/GoldenDict/content/youdao.mdx'
		resemble.compile_mdx(fn)

	test2()



