##
## $Release: 1.0.1 $
## $Copyright: copyright(c) 2007-2011 kuwata-lab.com all rights reserved. $
## $License: MIT License $
##
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##

"""Very fast and light-weight template engine based embedded Python.
   See User's Guide and examples for details.
   http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
   http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
"""

__version__  = "$Release: 1.0.1 $"[10:-2]
__license__  = "$License: MIT License $"[10:-2]
__all__      = ('Template', 'Engine', )


import sys, os, re, time, marshal
from time import time as _time
from os.path import getmtime as _getmtime
from os.path import isfile as _isfile
random = pickle = unquote = None   # lazy import
python3 = sys.version_info[0] == 3
python2 = sys.version_info[0] == 2

logger = None


##
## utilities
##

def _write_binary_file(filename, content):
    global random
    if random is None: from random import random
    tmpfile = filename + str(random())[1:]
    f = open(tmpfile, 'w+b')     # on windows, 'w+b' is preffered than 'wb'
    try:
        f.write(content)
    finally:
        f.close()
    if os.path.exists(tmpfile):
        try:
            os.rename(tmpfile, filename)
        except:
            os.remove(filename)  # on windows, existing file should be removed before renaming
            os.rename(tmpfile, filename)

def _read_binary_file(filename):
    f = open(filename, 'rb')
    try:
        return f.read()
    finally:
        f.close()

codecs = None    # lazy import

def _read_text_file(filename, encoding=None):
    global codecs
    if not codecs: import codecs
    f = codecs.open(filename, encoding=(encoding or 'utf-8'))
    try:
        return f.read()
    finally:
        f.close()

def _read_template_file(filename, encoding=None):
    s = _read_binary_file(filename)          ## binary(=str)
    if encoding: s = s.decode(encoding)      ## binary(=str) to unicode
    return s

_basestring = basestring
_unicode    = unicode
_bytes      = str

def _ignore_not_found_error(f, default=None):
    try:
        return f()
    except OSError, ex:
        if ex.errno == 2:   # error: No such file or directory
            return default
        raise

def create_module(module_name, dummy_func=None, **kwargs):
    """ex. mod = create_module('tenjin.util')"""
    mod = type(sys)(module_name)
    mod.__file__ = __file__
    mod.__dict__.update(kwargs)
    sys.modules[module_name] = mod
    if dummy_func:
        exec(dummy_func.func_code, mod.__dict__)
    return mod

def _raise(exception_class, *args):
    raise exception_class(*args)


##
## helper method's module
##

def _dummy():
    global unquote
    unquote = None
    global to_str, escape, echo, new_cycle, generate_tostrfunc
    global start_capture, stop_capture, capture_as, captured_as, CaptureContext
    global _p, _P, _decode_params

    def generate_tostrfunc(encode=None, decode=None):
        """Generate 'to_str' function with encode or decode encoding.
           ex. generate to_str() function which encodes unicode into binary(=str).
              to_str = tenjin.generate_tostrfunc(encode='utf-8')
              repr(to_str(u'hoge'))  #=> 'hoge' (str)
           ex. generate to_str() function which decodes binary(=str) into unicode.
              to_str = tenjin.generate_tostrfunc(decode='utf-8')
              repr(to_str('hoge'))   #=> u'hoge' (unicode)
        """
        if encode:
            if decode:
                raise ValueError("can't specify both encode and decode encoding.")
            else:
                def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance, _encode=encode):
                    """Convert val into string or return '' if None. Unicode will be encoded into binary(=str)."""
                    if _isa(val, _str):     return val
                    if val is None:         return ''
                    #if _isa(val, _unicode): return val.encode(_encode)  # unicode to binary(=str)
                    if _isa(val, _unicode):
                        return val.encode(_encode)  # unicode to binary(=str)
                    return _str(val)
        else:
            if decode:
                def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance, _decode=decode):
                    """Convert val into string or return '' if None. Binary(=str) will be decoded into unicode."""
                    #if _isa(val, _str):     return val.decode(_decode)  # binary(=str) to unicode
                    if _isa(val, _str):
                        return val.decode(_decode)
                    if val is None:         return ''
                    if _isa(val, _unicode): return val
                    return _unicode(val)
            else:
                def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance):
                    """Convert val into string or return '' if None. Both binary(=str) and unicode will be retruned as-is."""
                    if _isa(val, _str):     return val
                    if val is None:         return ''
                    if _isa(val, _unicode): return val
                    return _str(val)
        return to_str

    to_str = generate_tostrfunc(encode='utf-8')  # or encode=None?

    def echo(string):
        """add string value into _buf. this is equivarent to '#{string}'."""
        lvars = sys._getframe(1).f_locals   # local variables
        lvars['_buf'].append(string)

    def new_cycle(*values):
        """Generate cycle object.
           ex.
             cycle = new_cycle('odd', 'even')
             print(cycle())   #=> 'odd'
             print(cycle())   #=> 'even'
             print(cycle())   #=> 'odd'
             print(cycle())   #=> 'even'
        """
        def gen(values):
            i, n = 0, len(values)
            while True:
                yield values[i]
                i = (i + 1) % n
        return gen(values).next

    class CaptureContext(object):

        def __init__(self, name, store_to_context=True, lvars=None):
            self.name  = name
            self.store_to_context = store_to_context
            self.lvars = lvars or sys._getframe(1).f_locals

        def __enter__(self):
            lvars = self.lvars
            self._buf_orig = lvars['_buf']
            lvars['_buf']    = _buf = []
            lvars['_extend'] = _buf.extend
            return self

        def __exit__(self, *args):
            lvars = self.lvars
            _buf = lvars['_buf']
            lvars['_buf']    = self._buf_orig
            lvars['_extend'] = self._buf_orig.extend
            lvars[self.name] = self.captured = ''.join(_buf)
            if self.store_to_context and '_context' in lvars:
                lvars['_context'][self.name] = self.captured

        def __iter__(self):
            self.__enter__()
            yield self
            self.__exit__()

    def start_capture(varname=None, _depth=1):
        """(obsolete) start capturing with name."""
        lvars = sys._getframe(_depth).f_locals
        capture_context = CaptureContext(varname, None, lvars)
        lvars['_capture_context'] = capture_context
        capture_context.__enter__()

    def stop_capture(store_to_context=True, _depth=1):
        """(obsolete) stop capturing and return the result of capturing.
           if store_to_context is True then the result is stored into _context[varname].
        """
        lvars = sys._getframe(_depth).f_locals
        capture_context = lvars.pop('_capture_context', None)
        if not capture_context:
            raise Exception('stop_capture(): start_capture() is not called before.')
        capture_context.store_to_context = store_to_context
        capture_context.__exit__()
        return capture_context.captured

    def capture_as(name, store_to_context=True):
        """capture partial of template."""
        return CaptureContext(name, store_to_context, sys._getframe(1).f_locals)

    def captured_as(name, _depth=1):
        """helper method for layout template.
           if captured string is found then append it to _buf and return True,
           else return False.
        """
        lvars = sys._getframe(_depth).f_locals   # local variables
        if name in lvars:
            _buf = lvars['_buf']
            _buf.append(lvars[name])
            return True
        return False

    def _p(arg):
        """ex. '/show/'+_p("item['id']") => "/show/#{item['id']}" """
        return '<`#%s#`>' % arg    # decoded into #{...} by preprocessor

    def _P(arg):
        """ex. '<b>%s</b>' % _P("item['id']") => "<b>${item['id']}</b>" """
        return '<`$%s$`>' % arg    # decoded into ${...} by preprocessor

    def _decode_params(s):
        """decode <`#...#`> and <`$...$`> into #{...} and ${...}"""
        global unquote
        if unquote is None:
            from urllib import unquote
        dct = { 'lt':'<', 'gt':'>', 'amp':'&', 'quot':'"', '#039':"'", }
        def unescape(s):
            #return s.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#039;', "'").replace('&amp;',  '&')
            return re.sub(r'&(lt|gt|quot|amp|#039);',  lambda m: dct[m.group(1)],  s)
        s = to_str(s)
        s = re.sub(r'%3C%60%23(.*?)%23%60%3E', lambda m: '#{%s}' % unquote(m.group(1)), s)
        s = re.sub(r'%3C%60%24(.*?)%24%60%3E', lambda m: '${%s}' % unquote(m.group(1)), s)
        s = re.sub(r'&lt;`#(.*?)#`&gt;',   lambda m: '#{%s}' % unescape(m.group(1)), s)
        s = re.sub(r'&lt;`\$(.*?)\$`&gt;', lambda m: '${%s}' % unescape(m.group(1)), s)
        s = re.sub(r'<`#(.*?)#`>', r'#{\1}', s)
        s = re.sub(r'<`\$(.*?)\$`>', r'${\1}', s)
        return s

helpers = create_module('tenjin.helpers', _dummy, sys=sys, re=re)
helpers.__all__ = ['to_str', 'escape', 'echo', 'new_cycle', 'generate_tostrfunc',
                   'start_capture', 'stop_capture', 'capture_as', 'captured_as',
                   'not_cached', 'echo_cached', 'cache_as',
                   '_p', '_P', '_decode_params',
                   ]
generate_tostrfunc = helpers.generate_tostrfunc


##
## escaped module
##
def _dummy():
    global is_escaped, as_escaped, to_escaped
    global Escaped, EscapedStr, EscapedUnicode
    global __all__
    __all__ = ('is_escaped', 'as_escaped', 'to_escaped', ) #'Escaped', 'EscapedStr',

    class Escaped(object):
        """marking class that object is already escaped."""
        pass

    def is_escaped(value):
        """return True if value is marked as escaped, else return False."""
        return isinstance(value, Escaped)

    class EscapedStr(str, Escaped):
        """string class which is marked as escaped."""
        pass

    class EscapedUnicode(unicode, Escaped):
        """unicode class which is marked as escaped."""
        pass

    def as_escaped(s):
        """mark string as escaped, without escaping."""
        if isinstance(s, str):     return EscapedStr(s)
        if isinstance(s, unicode): return EscapedUnicode(s)
        raise TypeError("as_escaped(%r): expected str or unicode." % (s, ))

    def to_escaped(value):
        """convert any value into string and escape it.
           if value is already marked as escaped, don't escape it."""
        if hasattr(value, '__html__'):
            value = value.__html__()
        if is_escaped(value):
            #return value     # EscapedUnicode should be convered into EscapedStr
            return as_escaped(_helpers.to_str(value))
        #if isinstance(value, _basestring):
        #    return as_escaped(_helpers.escape(value))
        return as_escaped(_helpers.escape(_helpers.to_str(value)))

escaped = create_module('tenjin.escaped', _dummy, _helpers=helpers)


##
## module for html
##
def _dummy():
    global escape_html, escape_xml, escape, tagattr, tagattrs, _normalize_attrs
    global checked, selected, disabled, nl2br, text2html, nv, js_link

    #_escape_table = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
    #_escape_pattern = re.compile(r'[&<>"]')
    ##_escape_callable = lambda m: _escape_table[m.group(0)]
    ##_escape_callable = lambda m: _escape_table.__get__(m.group(0))
    #_escape_get     = _escape_table.__getitem__
    #_escape_callable = lambda m: _escape_get(m.group(0))
    #_escape_sub     = _escape_pattern.sub

    #def escape_html(s):
    #    return s                                          # 3.02

    #def escape_html(s):
    #    return _escape_pattern.sub(_escape_callable, s)   # 6.31

    #def escape_html(s):
    #    return _escape_sub(_escape_callable, s)           # 6.01

    #def escape_html(s, _p=_escape_pattern, _f=_escape_callable):
    #    return _p.sub(_f, s)                              # 6.27

    #def escape_html(s, _sub=_escape_pattern.sub, _callable=_escape_callable):
    #    return _sub(_callable, s)                         # 6.04

    #def escape_html(s):
    #    s = s.replace('&', '&amp;')
    #    s = s.replace('<', '&lt;')
    #    s = s.replace('>', '&gt;')
    #    s = s.replace('"', '&quot;')
    #    return s                                          # 5.83

    def escape_html(s):
        """Escape '&', '<', '>', '"' into '&amp;', '&lt;', '&gt;', '&quot;'."""
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')   # 5.72

    escape_xml = escape_html   # for backward compatibility

    def tagattr(name, expr, value=None, escape=True):
        """(experimental) Return ' name="value"' if expr is true value, else '' (empty string).
           If value is not specified, expr is used as value instead."""
        if not expr and expr != 0: return _escaped.as_escaped('')
        if value is None: value = expr
        if escape: value = _escaped.to_escaped(value)
        return _escaped.as_escaped(' %s="%s"' % (name, value))

    def tagattrs(**kwargs):
        """(experimental) built html tag attribtes.
           ex.
           >>> tagattrs(klass='main', size=20)
           ' class="main" size="20"'
           >>> tagattrs(klass='', size=0)
           ''
        """
        kwargs = _normalize_attrs(kwargs)
        esc = _escaped.to_escaped
        s = ''.join([ ' %s="%s"' % (k, esc(v)) for k, v in kwargs.iteritems() if v or v == 0 ])
        return _escaped.as_escaped(s)

    def _normalize_attrs(kwargs):
        if 'klass'    in kwargs: kwargs['class']    = kwargs.pop('klass')
        if 'checked'  in kwargs: kwargs['checked']  = kwargs.pop('checked')  and 'checked'  or None
        if 'selected' in kwargs: kwargs['selected'] = kwargs.pop('selected') and 'selected' or None
        if 'disabled' in kwargs: kwargs['disabled'] = kwargs.pop('disabled') and 'disabled' or None
        return kwargs

    def checked(expr):
        """return ' checked="checked"' if expr is true."""
        return _escaped.as_escaped(expr and ' checked="checked"' or '')

    def selected(expr):
        """return ' selected="selected"' if expr is true."""
        return _escaped.as_escaped(expr and ' selected="selected"' or '')

    def disabled(expr):
        """return ' disabled="disabled"' if expr is true."""
        return _escaped.as_escaped(expr and ' disabled="disabled"' or '')

    def nl2br(text):
        """replace "\n" to "<br />\n" and return it."""
        if not text:
            return _escaped.as_escaped('')
        return _escaped.as_escaped(text.replace('\n', '<br />\n'))

    def text2html(text, use_nbsp=True):
        """(experimental) escape xml characters, replace "\n" to "<br />\n", and return it."""
        if not text:
            return _escaped.as_escaped('')
        s = _escaped.to_escaped(text)
        if use_nbsp: s = s.replace('  ', ' &nbsp;')
        #return nl2br(s)
        s = s.replace('\n', '<br />\n')
        return _escaped.as_escaped(s)

    def nv(name, value, sep=None, **kwargs):
        """(experimental) Build name and value attributes.
           ex.
           >>> nv('rank', 'A')
           'name="rank" value="A"'
           >>> nv('rank', 'A', '.')
           'name="rank" value="A" id="rank.A"'
           >>> nv('rank', 'A', '.', checked=True)
           'name="rank" value="A" id="rank.A" checked="checked"'
           >>> nv('rank', 'A', '.', klass='error', style='color:red')
           'name="rank" value="A" id="rank.A" class="error" style="color:red"'
        """
        name  = _escaped.to_escaped(name)
        value = _escaped.to_escaped(value)
        s = sep and 'name="%s" value="%s" id="%s"' % (name, value, name+sep+value) \
                or  'name="%s" value="%s"'         % (name, value)
        html = kwargs and s + tagattrs(**kwargs) or s
        return _escaped.as_escaped(html)

    def js_link(label, onclick, **kwargs):
        s = kwargs and tagattrs(**kwargs) or ''
        html = '<a href="javascript:undefined" onclick="%s;return false"%s>%s</a>' % \
                  (_escaped.to_escaped(onclick), s, _escaped.to_escaped(label))
        return _escaped.as_escaped(html)

html = create_module('tenjin.html', _dummy, helpers=helpers, _escaped=escaped)
helpers.escape = html.escape_html
helpers.html = html   # for backward compatibility


##
## utility function to set default encoding of template files
##
_template_encoding = (None, 'utf-8')    # encodings for decode and encode

def set_template_encoding(decode=None, encode=None):
    """Set default encoding of template files.
       This should be called before importing helper functions.
       ex.
          ## I like template files to be unicode-base like Django.
          import tenjin
          tenjin.set_template_encoding('utf-8')  # should be called before importing helpers
          from tenjin.helpers import *
    """
    global _template_encoding
    if _template_encoding == (decode, encode):
        return
    if decode and encode:
        raise ValueError("set_template_encoding(): cannot specify both decode and encode.")
    if not decode and not encode:
        raise ValueError("set_template_encoding(): decode or encode should be specified.")
    if decode:
        Template.encoding = decode    # unicode base template
        helpers.to_str = helpers.generate_tostrfunc(decode=decode)
    else:
        Template.encoding = None      # binary base template
        helpers.to_str = helpers.generate_tostrfunc(encode=encode)
    _template_encoding = (decode, encode)


##
## Template class
##

class TemplateSyntaxError(SyntaxError):

    def build_error_message(self):
        ex = self
        if not ex.text:
            return self.args[0]
        return ''.join([
            "%s:%s:%s: %s\n" % (ex.filename, ex.lineno, ex.offset, ex.msg, ),
            "%4d: %s\n"      % (ex.lineno, ex.text.rstrip(), ),
            "     %s^\n"     % (' ' * ex.offset, ),
        ])


class Template(object):
    """Convert and evaluate embedded python string.
       See User's Guide and examples for details.
       http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
       http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
    """

    ## default value of attributes
    filename   = None
    encoding   = None
    escapefunc = 'escape'
    tostrfunc  = 'to_str'
    indent     = 8
    preamble   = None    # "_buf = []; _expand = _buf.expand; _to_str = to_str; _escape = escape"
    postamble  = None    # "print ''.join(_buf)"
    smarttrim  = None
    args       = None
    timestamp  = None
    trace      = False   # if True then '<!-- begin: file -->' and '<!-- end: file -->' are printed

    def __init__(self, filename=None, encoding=None, input=None, escapefunc=None, tostrfunc=None,
                       indent=None, preamble=None, postamble=None, smarttrim=None, trace=None):
        """Initailizer of Template class.

           filename:str (=None)
             Filename to convert (optional). If None, no convert.
           encoding:str (=None)
             Encoding name. If specified, template string is converted into
             unicode object internally.
             Template.render() returns str object if encoding is None,
             else returns unicode object if encoding name is specified.
           input:str (=None)
             Input string. In other words, content of template file.
             Template file will not be read if this argument is specified.
           escapefunc:str (='escape')
             Escape function name.
           tostrfunc:str (='to_str')
             'to_str' function name.
           indent:int (=8)
             Indent width.
           preamble:str or bool (=None)
             Preamble string which is inserted into python code.
             If true, '_buf = []; ' is used insated.
           postamble:str or bool (=None)
             Postamble string which is appended to python code.
             If true, 'print("".join(_buf))' is used instead.
           smarttrim:bool (=None)
             If True then "<div>\\n#{_context}\\n</div>" is parsed as
             "<div>\\n#{_context}</div>".
        """
        if encoding   is not None:  self.encoding   = encoding
        if escapefunc is not None:  self.escapefunc = escapefunc
        if tostrfunc  is not None:  self.tostrfunc  = tostrfunc
        if indent     is not None:  self.indent     = indent
        if preamble   is not None:  self.preamble   = preamble
        if postamble  is not None:  self.postamble  = postamble
        if smarttrim  is not None:  self.smarttrim  = smarttrim
        if trace      is not None:  self.trace      = trace
        #
        if preamble  is True:  self.preamble  = "_buf = []"
        if postamble is True:  self.postamble = "print(''.join(_buf))"
        if input:
            self.convert(input, filename)
            self.timestamp = False      # False means 'file not exist' (= Engine should not check timestamp of file)
        elif filename:
            self.convert_file(filename)
        else:
            self._reset()

    def _reset(self, input=None, filename=None):
        self.script   = None
        self.bytecode = None
        self.input    = input
        self.filename = filename
        if input != None:
            i = input.find("\n")
            if i < 0:
                self.newline = "\n"   # or None
            elif len(input) >= 2 and input[i-1] == "\r":
                self.newline = "\r\n"
            else:
                self.newline = "\n"
        self._localvars_assignments_added = False

    def _localvars_assignments(self):
        return "_extend=_buf.extend;_to_str=%s;_escape=%s; " % (self.tostrfunc, self.escapefunc)

    def before_convert(self, buf):
        if self.preamble:
            eol = self.input.startswith('<?py') and "\n" or "; "
            buf.append(self.preamble + eol)

    def after_convert(self, buf):
        if self.postamble:
            if buf and not buf[-1].endswith("\n"):
                buf.append("\n")
            buf.append(self.postamble + "\n")

    def convert_file(self, filename):
        """Convert file into python script and return it.
           This is equivarent to convert(open(filename).read(), filename).
        """
        input = _read_template_file(filename)
        return self.convert(input, filename)

    def convert(self, input, filename=None):
        """Convert string in which python code is embedded into python script and return it.

           input:str
             Input string to convert into python code.
           filename:str (=None)
             Filename of input. this is optional but recommended to report errors.
        """
        if self.encoding and isinstance(input, str):
            input = input.decode(self.encoding)
        self._reset(input, filename)
        buf = []
        self.before_convert(buf)
        self.parse_stmts(buf, input)
        self.after_convert(buf)
        script = ''.join(buf)
        self.script = script
        return script

    STMT_PATTERN = (r'<\?py( |\t|\r?\n)(.*?) ?\?>([ \t]*\r?\n)?', re.S)

    def stmt_pattern(self):
        pat = self.STMT_PATTERN
        if isinstance(pat, tuple):
            pat = self.__class__.STMT_PATTERN = re.compile(*pat)
        return pat

    def parse_stmts(self, buf, input):
        if not input: return
        rexp = self.stmt_pattern()
        is_bol = True
        index = 0
        for m in rexp.finditer(input):
            mspace, code, rspace = m.groups()
            #mspace, close, rspace = m.groups()
            #code = input[m.start()+4+len(mspace):m.end()-len(close)-(rspace and len(rspace) or 0)]
            text = input[index:m.start()]
            index = m.end()
            ## detect spaces at beginning of line
            lspace = None
            if text == '':
                if is_bol:
                    lspace = ''
            elif text[-1] == '\n':
                lspace = ''
            else:
                rindex = text.rfind('\n')
                if rindex < 0:
                    if is_bol and text.isspace():
                        lspace, text = text, ''
                else:
                    s = text[rindex+1:]
                    if s.isspace():
                        lspace, text = s, text[:rindex+1]
            #is_bol = rspace is not None
            ## add text, spaces, and statement
            self.parse_exprs(buf, text, is_bol)
            is_bol = rspace is not None
            #if mspace == "\n":
            if mspace and mspace.endswith("\n"):
                code = "\n" + (code or "")
            #if rspace == "\n":
            if rspace and rspace.endswith("\n"):
                code = (code or "") + "\n"
            if code:
                code = self.statement_hook(code)
                m = self._match_to_args_declaration(code)
                if m:
                    self._add_args_declaration(buf, m)
                else:
                    self.add_stmt(buf, code)
        rest = input[index:]
        if rest:
            self.parse_exprs(buf, rest)
        self._arrange_indent(buf)

    def statement_hook(self, stmt):
        """expand macros and parse '#@ARGS' in a statement."""
        return stmt.replace("\r\n", "\n")   # Python can't handle "\r\n" in code

    def _match_to_args_declaration(self, stmt):
        if self.args is not None:
            return None
        args_pattern = r'^ *#@ARGS(?:[ \t]+(.*?))?$'
        return re.match(args_pattern, stmt)

    def _add_args_declaration(self, buf, m):
        arr = (m.group(1) or '').split(',')
        args = [];  declares = []
        for s in arr:
            arg = s.strip()
            if not s: continue
            if not re.match('^[a-zA-Z_]\w*$', arg):
                raise ValueError("%r: invalid template argument." % arg)
            args.append(arg)
            declares.append("%s = _context.get('%s'); " % (arg, arg))
        self.args = args
        #nl = stmt[m.end():]
        #if nl: declares.append(nl)
        buf.append(''.join(declares) + "\n")

    EXPR_PATTERN = (r'#\{(.*?)\}|\$\{(.*?)\}|\{=(?:=(.*?)=|(.*?))=\}', re.S)

    def expr_pattern(self):
        pat = self.EXPR_PATTERN
        if isinstance(pat, tuple):
            self.__class__.EXPR_PATTERN = pat = re.compile(*pat)
        return pat

    def get_expr_and_flags(self, match):
        expr1, expr2, expr3, expr4 = match.groups()
        if expr1 is not None: return expr1, (False, True)   # not escape,  call to_str
        if expr2 is not None: return expr2, (True,  True)   # call escape, call to_str
        if expr3 is not None: return expr3, (False, True)   # not escape,  call to_str
        if expr4 is not None: return expr4, (True,  True)   # call escape, call to_str

    def parse_exprs(self, buf, input, is_bol=False):
        buf2 = []
        self._parse_exprs(buf2, input, is_bol)
        if buf2:
            buf.append(''.join(buf2))

    def _parse_exprs(self, buf, input, is_bol=False):
        if not input: return
        self.start_text_part(buf)
        rexp = self.expr_pattern()
        smarttrim = self.smarttrim
        nl = self.newline
        nl_len  = len(nl)
        pos = 0
        for m in rexp.finditer(input):
            start = m.start()
            text  = input[pos:start]
            pos   = m.end()
            expr, flags = self.get_expr_and_flags(m)
            #
            if text:
                self.add_text(buf, text)
            self.add_expr(buf, expr, *flags)
            #
            if smarttrim:
                flag_bol = text.endswith(nl) or not text and (start > 0  or is_bol)
                if flag_bol and not flags[0] and input[pos:pos+nl_len] == nl:
                    pos += nl_len
                    buf.append("\n")
        if smarttrim:
            if buf and buf[-1] == "\n":
                buf.pop()
        rest = input[pos:]
        if rest:
            self.add_text(buf, rest, True)
        self.stop_text_part(buf)
        if input[-1] == '\n':
            buf.append("\n")

    def start_text_part(self, buf):
        self._add_localvars_assignments_to_text(buf)
        #buf.append("_buf.extend((")
        buf.append("_extend((")

    def _add_localvars_assignments_to_text(self, buf):
        if not self._localvars_assignments_added:
            self._localvars_assignments_added = True
            buf.append(self._localvars_assignments())

    def stop_text_part(self, buf):
        buf.append("));")

    def _quote_text(self, text):
        return re.sub(r"(['\\\\])", r"\\\1", text)

    def add_text(self, buf, text, encode_newline=False):
        if not text: return
        use_unicode = self.encoding and python2
        buf.append(use_unicode and "u'''" or "'''")
        text = self._quote_text(text)
        if   not encode_newline:    buf.extend((text,       "''', "))
        elif text.endswith("\r\n"): buf.extend((text[0:-2], "\\r\\n''', "))
        elif text.endswith("\n"):   buf.extend((text[0:-1], "\\n''', "))
        else:                       buf.extend((text,       "''', "))

    _add_text = add_text

    def add_expr(self, buf, code, *flags):
        if not code or code.isspace(): return
        flag_escape, flag_tostr = flags
        if not self.tostrfunc:  flag_tostr  = False
        if not self.escapefunc: flag_escape = False
        if flag_tostr and flag_escape: s1, s2 = "_escape(_to_str(", ")), "
        elif flag_tostr:               s1, s2 = "_to_str(", "), "
        elif flag_escape:              s1, s2 = "_escape(", "), "
        else:                          s1, s2 = "(", "), "
        buf.extend((s1, code, s2, ))

    def add_stmt(self, buf, code):
        if not code: return
        lines = code.splitlines(True)   # keep "\n"
        if lines[-1][-1] != "\n":
            lines[-1] = lines[-1] + "\n"
        buf.extend(lines)
        self._add_localvars_assignments_to_stmts(buf)

    def _add_localvars_assignments_to_stmts(self, buf):
        if self._localvars_assignments_added:
            return
        for index, stmt in enumerate(buf):
            if not re.match(r'^[ \t]*(?:\#|_buf ?= ?\[\]|from __future__)', stmt):
                break
        else:
            return
        self._localvars_assignments_added = True
        if re.match(r'^[ \t]*(if|for|while|def|with|class)\b', stmt):
            buf.insert(index, self._localvars_assignments() + "\n")
        else:
            buf[index] = self._localvars_assignments() + buf[index]


    _START_WORDS = dict.fromkeys(('for', 'if', 'while', 'def', 'try:', 'with', 'class'), True)
    _END_WORDS   = dict.fromkeys(('#end', '#endfor', '#endif', '#endwhile', '#enddef', '#endtry', '#endwith', '#endclass'), True)
    _CONT_WORDS  = dict.fromkeys(('elif', 'else:', 'except', 'except:', 'finally:'), True)
    _WORD_REXP   = re.compile(r'\S+')

    depth = -1

    ##
    ## ex.
    ##   input = r"""
    ##   if items:
    ##   _buf.extend(('<ul>\n', ))
    ##   i = 0
    ##   for item in items:
    ##   i += 1
    ##   _buf.extend(('<li>', to_str(item), '</li>\n', ))
    ##   #endfor
    ##   _buf.extend(('</ul>\n', ))
    ##   #endif
    ##   """[1:]
    ##   lines = input.splitlines(True)
    ##   block = self.parse_lines(lines)
    ##      #=>  [ "if items:\n",
    ##             [ "_buf.extend(('<ul>\n', ))\n",
    ##               "i = 0\n",
    ##               "for item in items:\n",
    ##               [ "i += 1\n",
    ##                 "_buf.extend(('<li>', to_str(item), '</li>\n', ))\n",
    ##               ],
    ##               "#endfor\n",
    ##               "_buf.extend(('</ul>\n', ))\n",
    ##             ],
    ##             "#endif\n",
    ##           ]
    def parse_lines(self, lines):
        block = []
        try:
            self._parse_lines(lines.__iter__(), False, block, 0)
        except StopIteration:
            if self.depth > 0:
                fname, linenum, colnum, linetext = self.filename, len(lines), None, None
                raise TemplateSyntaxError("unexpected EOF.", (fname, linenum, colnum, linetext))
        else:
            pass
        return block

    def _parse_lines(self, lines_iter, end_block, block, linenum):
        if block is None: block = []
        _START_WORDS = self._START_WORDS
        _END_WORDS   = self._END_WORDS
        _CONT_WORDS  = self._CONT_WORDS
        _WORD_REXP   = self._WORD_REXP
        get_line = lines_iter.next
        while True:
            line = get_line()
            linenum += line.count("\n")
            m = _WORD_REXP.search(line)
            if not m:
                block.append(line)
                continue
            word = m.group(0)
            if word in _END_WORDS:
                if word != end_block and word != '#end':
                    if end_block is False:
                        msg = "'%s' found but corresponding statement is missing." % (word, )
                    else:
                        msg = "'%s' expected but got '%s'." % (end_block, word)
                    colnum = m.start() + 1
                    raise TemplateSyntaxError(msg, (self.filename, linenum, colnum, line))
                return block, line, None, linenum
            elif line.endswith(':\n') or line.endswith(':\r\n'):
                if word in _CONT_WORDS:
                    return block, line, word, linenum
                elif word in _START_WORDS:
                    block.append(line)
                    self.depth += 1
                    cont_word = None
                    try:
                        child_block, line, cont_word, linenum = \
                            self._parse_lines(lines_iter, '#end'+word, [], linenum)
                        block.extend((child_block, line, ))
                        while cont_word:   # 'elif' or 'else:'
                            child_block, line, cont_word, linenum = \
                                self._parse_lines(lines_iter, '#end'+word, [], linenum)
                            block.extend((child_block, line, ))
                    except StopIteration:
                        msg = "'%s' is not closed." % (cont_word or word)
                        colnum = m.start() + 1
                        raise TemplateSyntaxError(msg, (self.filename, linenum, colnum, line))
                    self.depth -= 1
                else:
                    block.append(line)
            else:
                block.append(line)
        assert "unreachable"

    def _join_block(self, block, buf, depth):
        indent = ' ' * (self.indent * depth)
        for line in block:
            if isinstance(line, list):
                self._join_block(line, buf, depth+1)
            elif line.isspace():
                buf.append(line)
            else:
                buf.append(indent + line.lstrip())

    def _arrange_indent(self, buf):
        """arrange indentation of statements in buf"""
        block = self.parse_lines(buf)
        buf[:] = []
        self._join_block(block, buf, 0)


    def render(self, context=None, globals=None, _buf=None):
        """Evaluate python code with context dictionary.
           If _buf is None then return the result of evaluation as str,
           else return None.

           context:dict (=None)
             Context object to evaluate. If None then new dict is created.
           globals:dict (=None)
             Global object. If None then globals() is used.
           _buf:list (=None)
             If None then new list is created.
        """
        if context is None:
            locals = context = {}
        elif self.args is None:
            locals = context.copy()
        else:
            locals = {}
            if '_engine' in context:
                context.get('_engine').hook_context(locals)
        locals['_context'] = context
        if globals is None:
            globals = sys._getframe(1).f_globals
        bufarg = _buf
        if _buf is None:
            _buf = []
        locals['_buf'] = _buf
        if not self.bytecode:
            self.compile()
        if self.trace:
            _buf.append("<!-- ***** begin: %s ***** -->\n" % self.filename)
            exec(self.bytecode, globals, locals)
            _buf.append("<!-- ***** end: %s ***** -->\n" % self.filename)
        else:
            exec(self.bytecode, globals, locals)
        if bufarg is not None:
            return bufarg
        elif not logger:
            return ''.join(_buf)
        else:
            try:
                return ''.join(_buf)
            except UnicodeDecodeError, ex:
                logger.error("[tenjin.Template] " + str(ex))
                logger.error("[tenjin.Template] (_buf=%r)" % (_buf, ))
                raise

    def compile(self):
        """compile self.script into self.bytecode"""
        self.bytecode = compile(self.script, self.filename or '(tenjin)', 'exec')


##
## preprocessor class
##

class Preprocessor(Template):
    """Template class for preprocessing."""

    STMT_PATTERN = (r'<\?PY( |\t|\r?\n)(.*?) ?\?>([ \t]*\r?\n)?', re.S)

    EXPR_PATTERN = (r'#\{\{(.*?)\}\}|\$\{\{(.*?)\}\}|\{#=(?:=(.*?)=|(.*?))=#\}', re.S)

    def add_expr(self, buf, code, *flags):
        if not code or code.isspace():
            return
        code = "_decode_params(%s)" % code
        Template.add_expr(self, buf, code, *flags)


##
## cache storages
##

class CacheStorage(object):
    """[abstract] Template object cache class (in memory and/or file)"""

    def __init__(self):
        self.items = {}    # key: full path, value: template object

    def get(self, cachepath, create_template):
        """get template object. if not found, load attributes from cache file and restore  template object."""
        template = self.items.get(cachepath)
        if not template:
            dct = self._load(cachepath)
            if dct:
                template = create_template()
                for k in dct:
                    setattr(template, k, dct[k])
                self.items[cachepath] = template
        return template

    def set(self, cachepath, template):
        """set template object and save template attributes into cache file."""
        self.items[cachepath] = template
        dct = self._save_data_of(template)
        return self._store(cachepath, dct)

    def _save_data_of(self, template):
        return { 'args'  : template.args,   'bytecode' : template.bytecode,
                 'script': template.script, 'timestamp': template.timestamp }

    def unset(self, cachepath):
        """remove template object from dict and cache file."""
        self.items.pop(cachepath, None)
        return self._delete(cachepath)

    def clear(self):
        """remove all template objects and attributes from dict and cache file."""
        d, self.items = self.items, {}
        for k in d.iterkeys():
            self._delete(k)
        d.clear()

    def _load(self, cachepath):
        """(abstract) load dict object which represents template object attributes from cache file."""
        raise NotImplementedError.new("%s#_load(): not implemented yet." % self.__class__.__name__)

    def _store(self, cachepath, template):
        """(abstract) load dict object which represents template object attributes from cache file."""
        raise NotImplementedError.new("%s#_store(): not implemented yet." % self.__class__.__name__)

    def _delete(self, cachepath):
        """(abstract) remove template object from cache file."""
        raise NotImplementedError.new("%s#_delete(): not implemented yet." % self.__class__.__name__)


class MemoryCacheStorage(CacheStorage):

    def _load(self, cachepath):
        return None

    def _store(self, cachepath, template):
        pass

    def _delete(self, cachepath):
        pass


class FileCacheStorage(CacheStorage):

    def _load(self, cachepath):
        if not _isfile(cachepath): return None
        if logger: logger.info("[tenjin.%s] load cache (file=%r)" % (self.__class__.__name__, cachepath))
        data = _read_binary_file(cachepath)
        return self._restore(data)

    def _store(self, cachepath, dct):
        if logger: logger.info("[tenjin.%s] store cache (file=%r)" % (self.__class__.__name__, cachepath))
        data = self._dump(dct)
        _write_binary_file(cachepath, data)

    def _restore(self, data):
        raise NotImplementedError("%s._restore(): not implemented yet." % self.__class__.__name__)

    def _dump(self, dct):
        raise NotImplementedError("%s._dump(): not implemented yet." % self.__class__.__name__)

    def _delete(self, cachepath):
        _ignore_not_found_error(lambda: os.unlink(cachepath))


class MarshalCacheStorage(FileCacheStorage):

    def _restore(self, data):
        return marshal.loads(data)

    def _dump(self, dct):
        return marshal.dumps(dct)


class PickleCacheStorage(FileCacheStorage):

    def __init__(self, *args, **kwargs):
        global pickle
        if pickle is None:
            import cPickle as pickle
        FileCacheStorage.__init__(self, *args, **kwargs)

    def _restore(self, data):
        return pickle.loads(data)

    def _dump(self, dct):
        dct.pop('bytecode', None)
        return pickle.dumps(dct)


class TextCacheStorage(FileCacheStorage):

    def _restore(self, data):
        header, script = data.split("\n\n", 1)
        timestamp = encoding = args = None
        for line in header.split("\n"):
            key, val = line.split(": ", 1)
            if   key == 'timestamp':  timestamp = float(val)
            elif key == 'encoding':   encoding  = val
            elif key == 'args':       args      = val.split(', ')
        if encoding: script = script.decode(encoding)   ## binary(=str) to unicode
        return {'args': args, 'script': script, 'timestamp': timestamp}

    def _dump(self, dct):
        s = dct['script']
        if dct.get('encoding') and isinstance(s, unicode):
            s = s.encode(dct['encoding'])           ## unicode to binary(=str)
        sb = []
        sb.append("timestamp: %s\n" % dct['timestamp'])
        if dct.get('encoding'):
            sb.append("encoding: %s\n" % dct['encoding'])
        if dct.get('args') is not None:
            sb.append("args: %s\n" % ', '.join(dct['args']))
        sb.append("\n")
        sb.append(s)
        s = ''.join(sb)
        if python3:
            if isinstance(s, str):
                s = s.encode(dct.get('encoding') or 'utf-8')   ## unicode(=str) to binary
        return s

    def _save_data_of(self, template):
        dct = FileCacheStorage._save_data_of(self, template)
        dct['encoding'] = template.encoding
        return dct



##
## abstract class for data cache
##
class KeyValueStore(object):

    def get(self, key, *options):
        raise NotImplementedError("%s.get(): not implemented yet." % self.__class__.__name__)

    def set(self, key, value, *options):
        raise NotImplementedError("%s.set(): not implemented yet." % self.__class__.__name__)

    def delete(self, key, *options):
        raise NotImplementedError("%s.del(): not implemented yet." % self.__class__.__name__)

    def has(self, key, *options):
        raise NotImplementedError("%s.has(): not implemented yet." % self.__class__.__name__)


##
## memory base data cache
##
class MemoryBaseStore(KeyValueStore):

    def __init__(self):
        self.values = {}

    def get(self, key, original_timestamp=None):
        tupl = self.values.get(key)
        if not tupl:
            return None
        value, created_at, expires_at = tupl
        if original_timestamp is not None and created_at < original_timestamp:
            self.delete(key)
            return None
        if expires_at < _time():
            self.delete(key)
            return None
        return value

    def set(self, key, value, lifetime=0):
        created_at = _time()
        expires_at = lifetime and created_at + lifetime or 0
        self.values[key] = (value, created_at, expires_at)
        return True

    def delete(self, key):
        try:
            del self.values[key]
            return True
        except KeyError:
            return False

    def has(self, key):
        pair = self.values.get(key)
        if not pair:
            return False
        value, created_at, expires_at = pair
        if expires_at and expires_at < _time():
            self.delete(key)
            return False
        return True


##
## file base data cache
##
class FileBaseStore(KeyValueStore):

    lifetime = 604800   # = 60*60*24*7

    def __init__(self, root_path, encoding=None):
        if not os.path.isdir(root_path):
            raise ValueError("%r: directory not found." % (root_path, ))
        self.root_path = root_path
        if encoding is None and python3:
            encoding = 'utf-8'
        self.encoding = encoding

    _pat = re.compile(r'[^-.\/\w]')

    def filepath(self, key, _pat1=_pat):
        return os.path.join(self.root_path, _pat1.sub('_', key))

    def get(self, key, original_timestamp=None):
        fpath = self.filepath(key)
        #if not _isfile(fpath): return None
        stat = _ignore_not_found_error(lambda: os.stat(fpath), None)
        if stat is None:
            return None
        created_at = stat.st_ctime
        expires_at = stat.st_mtime
        if original_timestamp is not None and created_at < original_timestamp:
            self.delete(key)
            return None
        if expires_at < _time():
            self.delete(key)
            return None
        if self.encoding:
            f = lambda: _read_text_file(fpath, self.encoding)
        else:
            f = lambda: _read_binary_file(fpath)
        return _ignore_not_found_error(f, None)

    def set(self, key, value, lifetime=0):
        fpath = self.filepath(key)
        dirname = os.path.dirname(fpath)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        now = _time()
        if isinstance(value, _unicode):
            value = value.encode(self.encoding or 'utf-8')
        _write_binary_file(fpath, value)
        expires_at = now + (lifetime or self.lifetime)  # timestamp
        os.utime(fpath, (expires_at, expires_at))
        return True

    def delete(self, key):
        fpath = self.filepath(key)
        ret = _ignore_not_found_error(lambda: os.unlink(fpath), False)
        return ret != False

    def has(self, key):
        fpath = self.filepath(key)
        if not _isfile(fpath):
            return False
        if _getmtime(fpath) < _time():
            self.delete(key)
            return False
        return True



##
## html fragment cache helper class
##
class FragmentCacheHelper(object):
    """html fragment cache helper class."""

    lifetime = 60   # 1 minute
    prefix   = None

    def __init__(self, store, lifetime=None, prefix=None):
        self.store = store
        if lifetime is not None:  self.lifetime = lifetime
        if prefix   is not None:  self.prefix   = prefix

    def not_cached(self, cache_key, lifetime=None):
        """(obsolete. use cache_as() instead of this.)
           html fragment cache helper. see document of FragmentCacheHelper class."""
        context = sys._getframe(1).f_locals['_context']
        context['_cache_key'] = cache_key
        key = self.prefix and self.prefix + cache_key or cache_key
        value = self.store.get(key)
        if value:    ## cached
            if logger: logger.debug('[tenjin.not_cached] %r: cached.' % (cache_key, ))
            context[key] = value
            return False
        else:        ## not cached
            if logger: logger.debug('[tenjin.not_cached]: %r: not cached.' % (cache_key, ))
            if key in context: del context[key]
            if lifetime is None:  lifetime = self.lifetime
            context['_cache_lifetime'] = lifetime
            helpers.start_capture(cache_key, _depth=2)
            return True

    def echo_cached(self):
        """(obsolete. use cache_as() instead of this.)
           html fragment cache helper. see document of FragmentCacheHelper class."""
        f_locals = sys._getframe(1).f_locals
        context = f_locals['_context']
        cache_key = context.pop('_cache_key')
        key = self.prefix and self.prefix + cache_key or cache_key
        if key in context:    ## cached
            value = context.pop(key)
        else:                 ## not cached
            value = helpers.stop_capture(False, _depth=2)
            lifetime = context.pop('_cache_lifetime')
            self.store.set(key, value, lifetime)
        f_locals['_buf'].append(value)

    def functions(self):
        """(obsolete. use cache_as() instead of this.)"""
        return (self.not_cached, self.echo_cached)

    def cache_as(self, cache_key, lifetime=None):
        key = self.prefix and self.prefix + cache_key or cache_key
        _buf = sys._getframe(1).f_locals['_buf']
        value = self.store.get(key)
        if value:
            if logger: logger.debug('[tenjin.cache_as] %r: cache found.' % (cache_key, ))
            _buf.append(value)
        else:
            if logger: logger.debug('[tenjin.cache_as] %r: expired or not cached yet.' % (cache_key, ))
            _buf_len = len(_buf)
            yield None
            value = ''.join(_buf[_buf_len:])
            self.store.set(key, value, lifetime)

## you can change default store by 'tenjin.helpers.fragment_cache.store = ...'
helpers.fragment_cache = FragmentCacheHelper(MemoryBaseStore())
helpers.not_cached  = helpers.fragment_cache.not_cached
helpers.echo_cached = helpers.fragment_cache.echo_cached
helpers.cache_as    = helpers.fragment_cache.cache_as
helpers.__all__.extend(('not_cached', 'echo_cached', 'cache_as'))



##
## helper class to find and read template
##
class Loader(object):

    def exists(self, filepath):
        raise NotImplementedError("%s.exists(): not implemented yet." % self.__class__.__name__)

    def find(self, filename, dirs=None):
        #: if dirs provided then search template file from it.
        if dirs:
            for dirname in dirs:
                filepath = os.path.join(dirname, filename)
                if self.exists(filepath):
                    return filepath
        #: if dirs not provided then just return filename if file exists.
        else:
            if self.exists(filename):
                return filename
        #: if file not found then return None.
        return None

    def abspath(self, filename):
        raise NotImplementedError("%s.abspath(): not implemented yet." % self.__class__.__name__)

    def timestamp(self, filepath):
        raise NotImplementedError("%s.timestamp(): not implemented yet." % self.__class__.__name__)

    def load(self, filepath):
        raise NotImplementedError("%s.timestamp(): not implemented yet." % self.__class__.__name__)



##
## helper class to find and read files
##
class FileSystemLoader(Loader):

    def exists(self, filepath):
        #: return True if filepath exists as a file.
        return os.path.isfile(filepath)

    def abspath(self, filepath):
        #: return full-path of filepath
        return os.path.abspath(filepath)

    def timestamp(self, filepath):
        #: return mtime of file
        return _getmtime(filepath)

    def load(self, filepath):
        #: if file exists, return file content and mtime
        def f():
            mtime = _getmtime(filepath)
            input = _read_template_file(filepath)
            mtime2 = _getmtime(filepath)
            if mtime != mtime2:
                mtime = mtime2
                input = _read_template_file(filepath)
                mtime2 = _getmtime(filepath)
                if mtime != mtime2:
                    if logger:
                        logger.warn("[tenjin] %s.load(): timestamp is changed while reading file." % self.__class__.__name__)
            return input, mtime
        #: if file not exist, return None
        return _ignore_not_found_error(f)


##
##
##
class TemplateNotFoundError(Exception):
    pass



##
## template engine class
##

class Engine(object):
    """Template Engine class.
       See User's Guide and examples for details.
       http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
       http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
    """

    ## default value of attributes
    prefix     = ''
    postfix    = ''
    layout     = None
    templateclass = Template
    path       = None
    cache      = MarshalCacheStorage()  # save converted Python code into file by marshal-format
    lang       = None
    loader     = FileSystemLoader()
    preprocess = False
    preprocessorclass = Preprocessor
    timestamp_interval = 1  # seconds

    def __init__(self, prefix=None, postfix=None, layout=None, path=None, cache=True, preprocess=None, templateclass=None, preprocessorclass=None, lang=None, loader=None, **kwargs):
        """Initializer of Engine class.

           prefix:str (='')
             Prefix string used to convert template short name to template filename.
           postfix:str (='')
             Postfix string used to convert template short name to template filename.
           layout:str (=None)
             Default layout template name.
           path:list of str(=None)
             List of directory names which contain template files.
           cache:bool or CacheStorage instance (=True)
             Cache storage object to store converted python code.
             If True, default cache storage (=Engine.cache) is used (if it is None
             then create MarshalCacheStorage object for each engine object).
             If False, no cache storage is used nor no cache files are created.
           preprocess:bool(=False)
             Activate preprocessing or not.
           templateclass:class (=Template)
             Template class which engine creates automatically.
           lang:str (=None)
             Language name such as 'en', 'fr', 'ja', and so on. If you specify
             this, cache file path will be 'inex.html.en.cache' for example.
           kwargs:dict
             Options for Template class constructor.
             See document of Template.__init__() for details.
        """
        if prefix:  self.prefix  = prefix
        if postfix: self.postfix = postfix
        if layout:  self.layout  = layout
        if templateclass: self.templateclass = templateclass
        if preprocessorclass: self.preprocessorclass = preprocessorclass
        if path is not None:  self.path = path
        if lang is not None:  self.lang = lang
        if loader is not None: self.loader = loader
        if preprocess is not None: self.preprocess = preprocess
        self.kwargs = kwargs
        self.encoding = kwargs.get('encoding')
        self._filepaths = {}   # template_name => relative path and absolute path
        self._added_templates = {}   # templates added by add_template()
        #self.cache = cache
        self._set_cache_storage(cache)

    def _set_cache_storage(self, cache):
        if cache is True:
            if not self.cache:
                self.cache = MarshalCacheStorage()
        elif cache is None:
            pass
        elif cache is False:
            self.cache = None
        elif isinstance(cache, CacheStorage):
            self.cache = cache
        else:
            raise ValueError("%r: invalid cache object." % (cache, ))

    def cachename(self, filepath):
        #: if lang is provided then add it to cache filename.
        if self.lang:
            return '%s.%s.cache' % (filepath, self.lang)
        #: return cache file name.
        else:
            return filepath + '.cache'

    def to_filename(self, template_name):
        """Convert template short name into filename.
           ex.
             >>> engine = tenjin.Engine(prefix='user_', postfix='.pyhtml')
             >>> engine.to_filename(':list')
             'user_list.pyhtml'
             >>> engine.to_filename('list')
             'list'
        """
        #: if template_name starts with ':', add prefix and postfix to it.
        if template_name[0] == ':' :
            return self.prefix + template_name[1:] + self.postfix
        #: if template_name doesn't start with ':', just return it.
        return template_name

    def _create_template(self, input=None, filepath=None, _context=None, _globals=None):
        #: if input is not specified then just create empty template object.
        template = self.templateclass(None, **self.kwargs)
        #: if input is specified then create template object and return it.
        if input:
            template.convert(input, filepath)
        return template

    def _preprocess(self, input, filepath, _context, _globals):
        #if _context is None: _context = {}
        #if _globals is None: _globals = sys._getframe(3).f_globals
        #: preprocess template and return result
        if '_engine' not in _context:
            self.hook_context(_context)
        preprocessor = self.preprocessorclass(filepath, input=input)
        return preprocessor.render(_context, globals=_globals)

    def add_template(self, template):
        self._added_templates[template.filename] = template

    def _get_template_from_cache(self, cachepath, filepath):
        #: if template not found in cache, return None
        template = self.cache.get(cachepath, self.templateclass)
        if not template:
            return None
        assert template.timestamp is not None
        #: if checked within a sec, skip timestamp check.
        now = _time()
        last_checked = getattr(template, '_last_checked_at', None)
        if last_checked and now < last_checked + self.timestamp_interval:
            #if logger: logger.trace('[tenjin.%s] timestamp check skipped (%f < %f + %f)' % \
            #                        (self.__class__.__name__, now, template._last_checked_at, self.timestamp_interval))
            return template
        #: if timestamp of template objectis same as file, return it.
        if template.timestamp == self.loader.timestamp(filepath):
            template._last_checked_at = now
            return template
        #: if timestamp of template object is different from file, clear it
        #cache._delete(cachepath)
        if logger: logger.info("[tenjin.%s] cache expired (filepath=%r)" % \
                                   (self.__class__.__name__, filepath))
        return None

    def get_template(self, template_name, _context=None, _globals=None):
        """Return template object.
           If template object has not registered, template engine creates
           and registers template object automatically.
        """
        #: accept template_name such as ':index'.
        filename = self.to_filename(template_name)
        #: if template object is added by add_template(), return it.
        if filename in self._added_templates:
            return self._added_templates[filename]
        #: get filepath and fullpath of template
        pair = self._filepaths.get(filename)
        if pair:
            filepath, fullpath = pair
        else:
            #: if template file is not found then raise TemplateNotFoundError.
            filepath = self.loader.find(filename, self.path)
            if not filepath:
                raise TemplateNotFoundError('%s: filename not found (path=%r).' % (filename, self.path))
            #
            fullpath = self.loader.abspath(filepath)
            self._filepaths[filename] = (filepath, fullpath)
        #: use full path as base of cache file path
        cachepath = self.cachename(fullpath)
        #: get template object from cache
        cache = self.cache
        template = cache and self._get_template_from_cache(cachepath, filepath) or None
        #: if template object is not found in cache or is expired...
        if not template:
            ret = self.loader.load(filepath)
            if not ret:
                raise TemplateNotFoundError("%r: template not found." % filepath)
            input, timestamp = ret
            if self.preprocess:   ## required for preprocessing
                if _context is None: _context = {}
                if _globals is None: _globals = sys._getframe(1).f_globals
                input = self._preprocess(input, filepath, _context, _globals)
            #: create template object.
            template = self._create_template(input, filepath, _context, _globals)
            #: set timestamp and filename of template object.
            template.timestamp = timestamp
            template._last_checked_at = _time()
            #: save template object into cache.
            if cache:
                if not template.bytecode: template.compile()
                cache.set(cachepath, template)
        #else:
        #    template.compile()
        #:
        template.filename = filepath
        return template

    def include(self, template_name, append_to_buf=True, **kwargs):
        """Evaluate template using current local variables as context.

           template_name:str
             Filename (ex. 'user_list.pyhtml') or short name (ex. ':list') of template.
           append_to_buf:boolean (=True)
             If True then append output into _buf and return None,
             else return stirng output.

           ex.
             <?py include('file.pyhtml') ?>
             #{include('file.pyhtml', False)}
             <?py val = include('file.pyhtml', False) ?>
        """
        #: get local and global vars of caller.
        frame = sys._getframe(1)
        locals  = frame.f_locals
        globals = frame.f_globals
        #: get _context from caller's local vars.
        assert '_context' in locals
        context = locals['_context']
        #: if kwargs specified then add them into context.
        if kwargs:
            context.update(kwargs)
        #: get template object with context data and global vars.
        ## (context and globals are passed to get_template() only for preprocessing.)
        template = self.get_template(template_name, context, globals)
        #: if append_to_buf is true then add output to _buf.
        #: if append_to_buf is false then don't add output to _buf.
        if append_to_buf:  _buf = locals['_buf']
        else:              _buf = None
        #: render template and return output.
        s = template.render(context, globals, _buf=_buf)
        #: kwargs are removed from context data.
        if kwargs:
            for k in kwargs:
                del context[k]
        return s

    def render(self, template_name, context=None, globals=None, layout=True):
        """Evaluate template with layout file and return result of evaluation.

           template_name:str
             Filename (ex. 'user_list.pyhtml') or short name (ex. ':list') of template.
           context:dict (=None)
             Context object to evaluate. If None then new dict is used.
           globals:dict (=None)
             Global context to evaluate. If None then globals() is used.
           layout:str or Bool(=True)
             If True, the default layout name specified in constructor is used.
             If False, no layout template is used.
             If str, it is regarded as layout template name.

           If temlate object related with the 'template_name' argument is not exist,
           engine generates a template object and register it automatically.
        """
        if context is None:
            context = {}
        if globals is None:
            globals = sys._getframe(1).f_globals
        self.hook_context(context)
        while True:
            ## context and globals are passed to get_template() only for preprocessing
            template = self.get_template(template_name, context, globals)
            content  = template.render(context, globals)
            layout   = context.pop('_layout', layout)
            if layout is True or layout is None:
                layout = self.layout
            if not layout:
                break
            template_name = layout
            layout = False
            context['_content'] = content
        context.pop('_content', None)
        return content

    def hook_context(self, context):
        #: add engine itself into context data.
        context['_engine'] = self
        #context['render'] = self.render
        #: add include() method into context data.
        context['include'] = self.include


##
## safe template and engine
##

class SafeTemplate(Template):
    """Uses 'to_escaped()' instead of 'escape()'.
       '#{...}' is not allowed with this class. Use '[==...==]' instead.
    """

    tostrfunc  = 'to_str'
    escapefunc = 'to_escaped'

    def get_expr_and_flags(self, match):
        return _get_expr_and_flags(match, "#{%s}: '#{}' is not allowed with SafeTemplate.")


class SafePreprocessor(Preprocessor):

    tostrfunc  = 'to_str'
    escapefunc = 'to_escaped'

    def get_expr_and_flags(self, match):
        return _get_expr_and_flags(match, "#{{%s}}: '#{{}}' is not allowed with SafePreprocessor.")


def _get_expr_and_flags(match, errmsg):
    expr1, expr2, expr3, expr4 = match.groups()
    if expr1 is not None:
        raise TemplateSyntaxError(errmsg % match.group(1))
    if expr2 is not None: return expr2, (True, False)   # #{...}    : call escape, not to_str
    if expr3 is not None: return expr3, (False, True)   # [==...==] : not escape, call to_str
    if expr4 is not None: return expr4, (True, False)   # [=...=]   : call escape, not to_str


class SafeEngine(Engine):

    templateclass     = SafeTemplate
    preprocessorclass = SafePreprocessor


del _dummy
