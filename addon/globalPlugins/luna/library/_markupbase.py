# -*- coding: UTF-8 -*-

import re

_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9]*\s*').match
_declstringlit_match = re.compile(r'(\'[^\']*\'|"[^"]*")\s*').match
_commentclose = re.compile(r'--\s*>')
_markedsectionclose = re.compile(r']\s*]\s*>')
_msmarkedsectionclose = re.compile(r']\s*>')

del re

class ParserBase:
	def __init__(self):
		if self.__class__ is ParserBase:
			raise RuntimeError(
				"_markupbase.ParserBase must be subclassed")

	def error(self, message):
		raise NotImplementedError(
			"subclasses of ParserBase must override error()")

	def reset(self):
		self.lineno = 1
		self.offset = 0

	def getpos(self):
		"""Return current line number and offset."""
		return self.lineno, self.offset

	def updatepos(self, i, j):
		if i >= j:
			return j
		rawdata = self.rawdata
		nlines = rawdata.count("\n", i, j)
		if nlines:
			self.lineno = self.lineno + nlines
			pos = rawdata.rindex("\n", i, j) # Should not fail
			self.offset = j-(pos+1)
		else:
			self.offset = self.offset + j-i
		return j

	_decl_otherchars = ''

	def parse_declaration(self, i):

		rawdata = self.rawdata
		j = i + 2
		assert rawdata[i:j] == "<!", "unexpected call to parse_declaration"
		if rawdata[j:j+1] == ">":
			return j + 1
		if rawdata[j:j+1] in ("-", ""):
			return -1
		n = len(rawdata)
		if rawdata[j:j+2] == '--': #comment
			return self.parse_comment(i)
		elif rawdata[j] == '[': #marked section
			return self.parse_marked_section(i)
		else:
			decltype, j = self._scan_name(j, i)
		if j < 0:
			return j
		if decltype == "doctype":
			self._decl_otherchars = ''
		while j < n:
			c = rawdata[j]
			if c == ">":
				data = rawdata[i+2:j]
				if decltype == "doctype":
					self.handle_decl(data)
				else:
					self.unknown_decl(data)
				return j + 1
			if c in "\"'":
				m = _declstringlit_match(rawdata, j)
				if not m:
					return -1 # incomplete
				j = m.end()
			elif c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
				name, j = self._scan_name(j, i)
			elif c in self._decl_otherchars:
				j = j + 1
			elif c == "[":
				if decltype == "doctype":
					j = self._parse_doctype_subset(j + 1, i)
				elif decltype in {"attlist", "linktype", "link", "element"}:
					self.error("unsupported '[' char in %s declaration" % decltype)
				else:
					self.error("unexpected '[' char in declaration")
			else:
				self.error(
					"unexpected %r char in declaration" % rawdata[j])
			if j < 0:
				return j
		return -1 # incomplete

	# Internal -- parse a marked section
	# Override this to handle MS-word extension syntax <![if word]>content<![endif]>
	def parse_marked_section(self, i, report=1):
		rawdata= self.rawdata
		assert rawdata[i:i+3] == '<![', "unexpected call to parse_marked_section()"
		sectName, j = self._scan_name( i+3, i )
		if j < 0:
			return j
		if sectName in {"temp", "cdata", "ignore", "include", "rcdata"}:
			# look for standard ]]> ending
			match= _markedsectionclose.search(rawdata, i+3)
		elif sectName in {"if", "else", "endif"}:
			# look for MS Office ]> ending
			match= _msmarkedsectionclose.search(rawdata, i+3)
		else:
			self.error('unknown status keyword %r in marked section' % rawdata[i+3:j])
		if not match:
			return -1
		if report:
			j = match.start(0)
			self.unknown_decl(rawdata[i+3: j])
		return match.end(0)

	# Internal -- parse comment, return length or -1 if not terminated
	def parse_comment(self, i, report=1):
		rawdata = self.rawdata
		if rawdata[i:i+4] != '<!--':
			self.error('unexpected call to parse_comment()')
		match = _commentclose.search(rawdata, i+4)
		if not match:
			return -1
		if report:
			j = match.start(0)
			self.handle_comment(rawdata[i+4: j])
		return match.end(0)

	# Internal -- scan past the internal subset in a <!DOCTYPE declaration,
	# returning the index just past any whitespace following the trailing ']'.
	def _parse_doctype_subset(self, i, declstartpos):
		rawdata = self.rawdata
		n = len(rawdata)
		j = i
		while j < n:
			c = rawdata[j]
			if c == "<":
				s = rawdata[j:j+2]
				if s == "<":
					# end of buffer; incomplete
					return -1
				if s != "<!":
					self.updatepos(declstartpos, j + 1)
					self.error("unexpected char in internal subset (in %r)" % s)
				if (j + 2) == n:
					# end of buffer; incomplete
					return -1
				if (j + 4) > n:
					# end of buffer; incomplete
					return -1
				if rawdata[j:j+4] == "<!--":
					j = self.parse_comment(j, report=0)
					if j < 0:
						return j
					continue
				name, j = self._scan_name(j + 2, declstartpos)
				if j == -1:
					return -1
				if name not in {"attlist", "element", "entity", "notation"}:
					self.updatepos(declstartpos, j + 2)
					self.error(
						"unknown declaration %r in internal subset" % name)
				# handle the individual names
				meth = getattr(self, "_parse_doctype_" + name)
				j = meth(j, declstartpos)
				if j < 0:
					return j
			elif c == "%":
				# parameter entity reference
				if (j + 1) == n:
					# end of buffer; incomplete
					return -1
				s, j = self._scan_name(j + 1, declstartpos)
				if j < 0:
					return j
				if rawdata[j] == ";":
					j = j + 1
			elif c == "]":
				j = j + 1
				while j < n and rawdata[j].isspace():
					j = j + 1
				if j < n:
					if rawdata[j] == ">":
						return j
					self.updatepos(declstartpos, j)
					self.error("unexpected char after internal subset")
				else:
					return -1
			elif c.isspace():
				j = j + 1
			else:
				self.updatepos(declstartpos, j)
				self.error("unexpected char %r in internal subset" % c)
		# end of buffer reached
		return -1

	# Internal -- scan past <!ELEMENT declarations
	def _parse_doctype_element(self, i, declstartpos):
		name, j = self._scan_name(i, declstartpos)
		if j == -1:
			return -1
		# style content model; just skip until '>'
		rawdata = self.rawdata
		if '>' in rawdata[j:]:
			return rawdata.find(">", j) + 1
		return -1

	# Internal -- scan past <!ATTLIST declarations
	def _parse_doctype_attlist(self, i, declstartpos):
		rawdata = self.rawdata
		name, j = self._scan_name(i, declstartpos)
		c = rawdata[j:j+1]
		if c == "":
			return -1
		if c == ">":
			return j + 1
		while 1:
			# scan a series of attribute descriptions; simplified:
			#   name type [value] [#constraint]
			name, j = self._scan_name(j, declstartpos)
			if j < 0:
				return j
			c = rawdata[j:j+1]
			if c == "":
				return -1
			if c == "(":
				# an enumerated type; look for ')'
				if ")" in rawdata[j:]:
					j = rawdata.find(")", j) + 1
				else:
					return -1
				while rawdata[j:j+1].isspace():
					j = j + 1
				if not rawdata[j:]:
					# end of buffer, incomplete
					return -1
			else:
				name, j = self._scan_name(j, declstartpos)
			c = rawdata[j:j+1]
			if not c:
				return -1
			if c in "'\"":
				m = _declstringlit_match(rawdata, j)
				if m:
					j = m.end()
				else:
					return -1
				c = rawdata[j:j+1]
				if not c:
					return -1
			if c == "#":
				if rawdata[j:] == "#":
					# end of buffer
					return -1
				name, j = self._scan_name(j + 1, declstartpos)
				if j < 0:
					return j
				c = rawdata[j:j+1]
				if not c:
					return -1
			if c == '>':
				# all done
				return j + 1

	# Internal -- scan past <!NOTATION declarations
	def _parse_doctype_notation(self, i, declstartpos):
		name, j = self._scan_name(i, declstartpos)
		if j < 0:
			return j
		rawdata = self.rawdata
		while 1:
			c = rawdata[j:j+1]
			if not c:
				# end of buffer; incomplete
				return -1
			if c == '>':
				return j + 1
			if c in "'\"":
				m = _declstringlit_match(rawdata, j)
				if not m:
					return -1
				j = m.end()
			else:
				name, j = self._scan_name(j, declstartpos)
				if j < 0:
					return j

	# Internal -- scan past <!ENTITY declarations
	def _parse_doctype_entity(self, i, declstartpos):
		rawdata = self.rawdata
		if rawdata[i:i+1] == "%":
			j = i + 1
			while 1:
				c = rawdata[j:j+1]
				if not c:
					return -1
				if c.isspace():
					j = j + 1
				else:
					break
		else:
			j = i
		name, j = self._scan_name(j, declstartpos)
		if j < 0:
			return j
		while 1:
			c = self.rawdata[j:j+1]
			if not c:
				return -1
			if c in "'\"":
				m = _declstringlit_match(rawdata, j)
				if m:
					j = m.end()
				else:
					return -1    # incomplete
			elif c == ">":
				return j + 1
			else:
				name, j = self._scan_name(j, declstartpos)
				if j < 0:
					return j

	# Internal -- scan a name token and the new position and the token, or
	# return -1 if we've reached the end of the buffer.
	def _scan_name(self, i, declstartpos):
		rawdata = self.rawdata
		n = len(rawdata)
		if i == n:
			return None, -1
		m = _declname_match(rawdata, i)
		if m:
			s = m.group()
			name = s.strip()
			if (i + len(s)) == n:
				return None, -1  # end of buffer
			return name.lower(), m.end()
		else:
			self.updatepos(declstartpos, i)
			self.error("expected name token at %r"
					   % rawdata[declstartpos:declstartpos+20])

	# To be overridden -- handlers for unknown objects
	def unknown_decl(self, data):
		pass