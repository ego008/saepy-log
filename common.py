# -*- coding: utf-8 -*-
#import logging
import re
import os.path
from traceback import format_exc
from urllib import unquote, quote, urlencode
from urlparse import urljoin, urlunsplit

from datetime import datetime, timedelta

import tenjin
from tenjin.helpers import *

from setting import *

import tornado.web


#Memcache 是否可用、用户是否在后台初始化Memcache
MC_Available = False
if PAGE_CACHE:
    import pylibmc
    mc = pylibmc.Client() #只需初始化一次？
    try:
        MC_Available = mc.set('mc_available', '1', 3600)
    except:
        pass

#####
def slugfy(text, separator='-'):
    text = text.lower()
    text = re.sub("[¿_\-　，。：；‘“’”【】『』§！－——＋◎＃￥％……※×（）《》？、÷]+", ' ', text)
    ret_list = []
    for c in text:
        ordnum = ord(c)
        if 47<ordnum<58 or 96<ordnum<123:
            ret_list.append(c)
        else:
            if re.search(u"[\u4e00-\u9fa5]", c):
                ret_list.append(c)
            else:
                ret_list.append(' ')
    ret = ''.join(ret_list)
    ret = re.sub(r"\ba\b|\ban\b|\bthe\b", '', ret)
    ret = ret.strip()
    ret = re.sub("[\s]+", separator, ret)
    return ret

def safe_encode(con):
    return con.replace("<","&lt;").replace(">","&gt;")

def safe_decode(con):
    return con.replace("&lt;","<").replace("&gt;",">")

def unquoted_unicode(string, coding='utf-8'):
    return unquote(string).decode(coding)

def quoted_string(unicode, coding='utf-8'):
    return quote(unicode.encode(coding))

def cnnow():
    return datetime.utcnow() + timedelta(hours =+ 8)

# get time_from_now
def timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)

def time_from_now(time):
    if isinstance(time, int):
        time = timestamp_to_datetime(time)
    #time_diff = datetime.utcnow() - time
    time_diff = cnnow() - time
    days = time_diff.days
    if days:
        if days > 730:
            return '%s years ago' % (days / 365)
        if days > 365:
            return '1 year ago'
        if days > 60:
            return '%s months ago' % (days / 30)
        if days > 30:
            return '1 month ago'
        if days > 14:
            return '%s weeks ago' % (days / 7)
        if days > 7:
            return '1 week ago'
        if days > 1:
            return '%s days ago' % days
        return '1 day ago'
    seconds = time_diff.seconds
    if seconds > 7200:
        return '%s hours ago' % (seconds / 3600)
    if seconds > 3600:
        return '1 hour ago'
    if seconds > 120:
        return '%s minutes ago' % (seconds / 60)
    if seconds > 60:
        return '1 minute ago'
    if seconds > 1:
        return '%s seconds ago' %seconds
    return '%s second ago' % seconds

def clear_cache_by_pathlist(pathlist = []):
    if pathlist and MC_Available:
        try:
            mc = pylibmc.Client()
            mc.delete_multi([str(p) for p in pathlist])
        except:
            pass

def clear_all_cache():
    if PAGE_CACHE:
        try:
            mc = pylibmc.Client()
            mc.flush_all()
        except:
            pass
    else:
        pass
    
def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def memcached(key, cache_time=0, key_suffix_calc_func=None):
    def wrap(func):
        def cached_func(*args, **kw):
            if not MC_Available:
                return func(*args, **kw)
            
            key_with_suffix = key
            if key_suffix_calc_func:
                key_suffix = key_suffix_calc_func(*args, **kw)
                if key_suffix is not None:
                    key_with_suffix = '%s:%s' % (key, key_suffix)
            
            mc = pylibmc.Client()
            value = mc.get(key_with_suffix)
            if value is None:
                value = func(*args, **kw)
                try:
                    mc.set(key_with_suffix, value, cache_time)
                except:
                    pass
            return value
        return cached_func
    return wrap

RQT_RE = re.compile('<span id="requesttime">\d*</span>', re.I)
def pagecache(key="", time=PAGE_CACHE_TIME, key_suffix_calc_func=None):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if not MC_Available:
                method(*args, **kwargs)
                return
            
            req = args[0]
            
            key_with_suffix = key
            if key_suffix_calc_func:
                key_suffix = key_suffix_calc_func(*args, **kwargs)
                if key_suffix:
                    key_with_suffix = '%s:%s' % (key, quoted_string(key_suffix)) 
            
            if key_with_suffix:
                key_with_suffix = str(key_with_suffix)
            else:
                key_with_suffix = req.request.path
                
            mc = pylibmc.Client()
            html = mc.get(key_with_suffix)
            request_time = int(req.request.request_time()*1000)
            if html:
                req.write(html)
                #req.write(RQT_RE.sub('<span id="requesttime">%d</span>'%request_time, html))
            else:
                result = method(*args, **kwargs)
                mc.set(key_with_suffix, result, time)
        return _wrapper
    return _decorate

###
engine = tenjin.Engine(path=[os.path.join('templates', theme) for theme in [THEME,'admin']] + ['templates'], cache=tenjin.MemoryCacheStorage(), preprocess=True)
class BaseHandler(tornado.web.RequestHandler):
    
    def render(self, template, context=None, globals=None, layout=False):
        if context is None:
            context = {}
        context.update({
            'request':self.request,
        })
        return engine.render(template, context, globals, layout)

    def echo(self, template, context=None, globals=None, layout=False):
        self.write(self.render(template, context, globals, layout))
    
    def set_cache(self, seconds, is_privacy=None):
        if seconds <= 0:
            self.set_header('Cache-Control', 'no-cache')
            #self.set_header('Expires', 'Fri, 01 Jan 1990 00:00:00 GMT')
        else:
            if is_privacy:
                privacy = 'public, '
            elif is_privacy is None:
                privacy = ''
            else:
                privacy = 'private, '
            self.set_header('Cache-Control', '%smax-age=%s' % (privacy, seconds))
    
def authorized(url='/admin/login'):
    def wrap(handler):
        def authorized_handler(self, *args, **kw):
            request = self.request
            user_name_cookie = self.get_cookie('username','')
            user_pw_cookie = self.get_cookie('userpw','')
            if user_name_cookie and user_pw_cookie:
                from model import User
                user = User.check_user(user_name_cookie, user_pw_cookie)
            else:
                user = False
            if request.method == 'GET':
                if not user:
                    self.redirect(url)
                    return False
                else:
                    handler(self, *args, **kw)
            else:
                if not user:
                    self.error(403)
                else:
                    handler(self, *args, **kw)
        return authorized_handler
    return wrap

def client_cache(seconds, privacy=None):
    def wrap(handler):
        def cache_handler(self, *args, **kw):
            self.set_cache(seconds, privacy)
            return handler(self, *args, **kw)
        return cache_handler
    return wrap
