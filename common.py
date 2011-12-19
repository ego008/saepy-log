# -*- coding: utf-8 -*-
#import logging
import re
import os.path
from traceback import format_exc
from urllib import unquote, quote, urlencode
from urlparse import urljoin, urlunsplit
#from os import environ
from datetime import datetime, timedelta

import tenjin
from tenjin.helpers import *

from setting import *

try:
    import tornado
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

def ping_hubs(feed):
    pass

def ping_xml_rpc(article_url):
    pass

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

def clear_article_memcache(id=''):
    tenjin.helpers.fragment_cache.store.delete('post_%s' % str(id))
    tenjin.helpers.fragment_cache.store.delete('post_comments_%s' % str(id))

def clear_sider_memcache():
    tenjin.helpers.fragment_cache.store.delete('sider')

def clear_index_memcache():
    tenjin.helpers.fragment_cache.store.delete('index_1')
    
def format_date(dt):
	return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

###
engine = tenjin.Engine(path=[os.path.join('templates', theme) for theme in THEMES] + ['templates'], cache=tenjin.MemoryCacheStorage(), preprocess=True)
class BaseHandler(tornado.web.RequestHandler):
        
    __SPIDER_PATTERN = re.compile('(bot|crawl|spider|slurp|sohu-search|lycos|robozilla)', re.I)
    
    def render(self, template, context=None, globals=None, layout=False):
        if context is None:
            context = {}
        context.update({
            'request':self.request,
            'is_spider':self.is_spider()
        })
        return engine.render(template, context, globals, layout)

    def echo(self, template, context=None, globals=None, layout=False):
        self.write(self.render(template, context, globals, layout))
    
    def is_spider(self):
        try:
            user_agent = self.request.headers['user_agent']
            return self.__SPIDER_PATTERN.search(user_agent) is not None
        except:
            return None
    
def authorized(url='/admin/login'):
    def wrap(handler):
        def authorized_handler(self, *args, **kw):
            request = self.request
            logged = self.get_cookie('logged','')
            #user_name_cookie = self.get_cookie('username','')
            #user_pw_cookie = self.get_cookie('userpw','')
            if logged and logged == '1':
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
    
