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
# generation
#----------------------------------------------------------------------
generator = Generator()


#----------------------------------------------------------------------
# testing case
#----------------------------------------------------------------------
if __name__ == '__main__':
	print ''



