# -*- coding: utf-8 -*-

import logging
import re

try:
    import json
except:
    import simplejson as json
    
from hashlib import md5
from time import time
from datetime import datetime,timedelta
from urllib import urlencode

from common import BaseHandler, authorized, safe_encode, cnnow, clear_cache_by_pathlist, quoted_string, clear_all_cache

from setting import *
from model import Article, Comment, Link, Category, Tag, User, MyData

if not debug:
    import sae.mail
    from sae.taskqueue import add_task
    import sae.storage
    
######
def put_obj2storage(file_name = '', data = '', expires='365', type=None, encoding= None, domain_name = STORAGE_DOMAIN_NAME):
    s = sae.storage.Client()
    ob = sae.storage.Object(data = data, cache_control='access plus %s day' % expires, content_type= type, content_encoding= encoding)
    return s.put(domain_name, file_name, ob)
    
    
######
class HomePage(BaseHandler):
    @authorized()
    def get(self):
        output = self.render('admin_index.html', {
            'title': "%s - %s"%(SITE_TITLE,SITE_SUB_TITLE),
            'keywords':KEYWORDS,
            'description':SITE_DECR,
            'test': '',
        },layout='_layout_admin.html')
        self.write(output)
        return output
    
class Login(BaseHandler):
    def get(self):
        self.echo('admin_login.html', {
            'title': "管理员登录",
            'has_user': User.check_has_user()
        },layout='_layout_admin.html')

    def post(self):
        try:
            name = self.get_argument("name")
            password = self.get_argument("password")
        except:
            self.redirect('%s/admin/login'% BASE_URL)
            return
        
        if name and password:
            has_user = User.check_has_user()
            if has_user:
                #check user
                password = md5(password.encode('utf-8')).hexdigest()
                user = User.check_user( name, password)
                if user:
                    #logging.error('user ok')
                    self.set_cookie('username', name, path="/", expires_days = 365 )
                    self.set_cookie('userpw', password, path="/", expires_days = 365 )
                    self.redirect('%s/admin/'% BASE_URL)
                    return
                else:
                    #logging.error('user not ok')
                    self.redirect('%s/admin/login'% BASE_URL)
                    return
            else:
                #add new user
                newuser = User.add_new_user( name, password)
                if newuser:
                    self.set_cookie('username', name, path="/", expires_days = 365 )
                    self.set_cookie('userpw', md5(password.encode('utf-8')).hexdigest(), path="/", expires_days = 365 )
                    self.redirect('%s/admin/'% BASE_URL)
                    return
                else:
                    self.redirect('%s/admin/login'% BASE_URL)
                    return
        else:
            self.redirect('%s/admin/login'% BASE_URL)

class Logout(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('%s/admin/login'% BASE_URL)

class AddUser(BaseHandler):
    @authorized()
    def get(self):
        pass
        
class Forbidden(BaseHandler):
    def get(self):
        self.write('Forbidden page')

class FileUpload(BaseHandler):
    @authorized()
    def post(self):
        self.set_header('Content-Type','text/html')
        rspd = {'status': 201, 'msg':'ok'}
        
        filetoupload = self.request.files['filetoupload']
        if filetoupload:
            myfile = filetoupload[0]
            try:
                file_type = myfile['filename'].split('.')[-1].lower()
                new_file_name = "%s.%s"% (str(int(time())), file_type)
            except:
                file_type = ''
                new_file_name = str(int(time()))
            ##
            mime_type = myfile['content_type']
            encoding = None
            ###
            
            try:
                attachment_url = put_obj2storage(file_name = new_file_name, data = myfile['body'], expires='365', type= mime_type, encoding= encoding)
            except:
                attachment_url = ''
            
            if attachment_url:
                rspd['status'] = 200
                rspd['filename'] = myfile['filename']
                rspd['msg'] = attachment_url
            else:
                rspd['status'] = 500
                rspd['msg'] = 'put_obj2storage erro, try it again.'
        else:
            rspd['msg'] = 'No file uploaded'
        self.write(json.dumps(rspd))
        return        
        
class AddPost(BaseHandler):
    @authorized()
    def get(self):
        self.echo('admin_addpost.html', {
            'title': "添加文章",
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_all_tag_name(),
        },layout='_layout_admin.html')        
    
    @authorized()
    def post(self):
        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}
                
        try:
            tf = {'true':1,'false':0}
            timestamp = int(time())
            post_dic = {
                'category': self.get_argument("cat"),
                'title': self.get_argument("tit"),
                'content': self.get_argument("con"),
                'tags': self.get_argument("tag",'').replace(u'，',','),
                'closecomment': self.get_argument("clo",'0'),
                'password': self.get_argument("password",''),
                'add_time': timestamp,
                'edit_time': timestamp,
            }
            if post_dic['tags']:
                tagslist = set([x.strip() for x in post_dic['tags'].split(',')])
                try:
                    tagslist.remove('')
                except:
                    pass
                if tagslist:
                    post_dic['tags'] = ','.join(tagslist)
            post_dic['closecomment'] = tf[post_dic['closecomment'].lower()]
        except:
            rspd['status'] = 500
            rspd['msg'] = '错误： 注意必填的三项'
            self.write(json.dumps(rspd))
            return
        
        postid = Article.add_new_article(post_dic)
        if postid:
            Category.add_postid_to_cat(post_dic['category'], str(postid))
            if post_dic['tags']:
                Tag.add_postid_to_tags(post_dic['tags'].split(','), str(postid))
            
            rspd['status'] = 200
            rspd['msg'] = '完成： 你已经成功添加了一篇文章 <a href="/t/%s" target="_blank">查看</a>' % str(postid)
            clear_cache_by_pathlist(['/', 'cat:%s' % quoted_string(post_dic['category'])])
            
            if not debug:
                add_task('default', '/task/pingrpctask')
            
            self.write(json.dumps(rspd))
            return
        else:
            rspd['status'] = 500
            rspd['msg'] = '错误： 未知错误，请尝试重新提交'
            self.write(json.dumps(rspd))
            return            
        
class EditPost(BaseHandler):
    @authorized()
    def get(self, id = ''):
        obj = None
        if id:
            obj = Article.get_article_by_id_edit(id)
        self.echo('admin_editpost.html', {
            'title': "编辑文章",
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_all_tag_name(),
            'obj': obj
        },layout='_layout_admin.html')        
    
    @authorized()
    def post(self, id = ''):
        act = self.get_argument("act",'')
        if act == 'findid':
            eid = self.get_argument("id",'')
            self.redirect('%s/admin/edit_post/%s'% (BASE_URL, eid))
            return
        
        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}
        oldobj = Article.get_article_by_id_edit(id)
        
        try:
            tf = {'true':1,'false':0}
            timestamp = int(time())
            post_dic = {
                'category': self.get_argument("cat"),
                'title': self.get_argument("tit"),
                'content': self.get_argument("con"),
                'tags': self.get_argument("tag",'').replace(u'，',','),
                'closecomment': self.get_argument("clo",'0'),
                'password': self.get_argument("password",''),
                'edit_time': timestamp,
                'id': id
            }
            
            if post_dic['tags']:
                tagslist = set([x.strip() for x in post_dic['tags'].split(',')])
                try:
                    tagslist.remove('')
                except:
                    pass
                if tagslist:
                    post_dic['tags'] = ','.join(tagslist)
            post_dic['closecomment'] = tf[post_dic['closecomment'].lower()]
        except:
            rspd['status'] = 500
            rspd['msg'] = '错误： 注意必填的三项'
            self.write(json.dumps(rspd))
            return
        
        postid = Article.update_post_edit(post_dic)
        if postid:
            cache_key_list = ['/', 'post:%s'% id, 'cat:%s' % quoted_string(oldobj.category)]
            if oldobj.category != post_dic['category']:
                #cat changed 
                Category.add_postid_to_cat(post_dic['category'], str(postid))
                Category.remove_postid_from_cat(post_dic['category'], str(postid))
                cache_key_list.append('cat:%s' % quoted_string(post_dic['category']))
            
            if oldobj.tags != post_dic['tags']:
                #tag changed 
                old_tags = set(oldobj.tags.split(','))
                new_tags = set(post_dic['tags'].split(','))
                
                removed_tags = old_tags - new_tags
                added_tags = new_tags - old_tags
                
                if added_tags:
                    Tag.add_postid_to_tags(added_tags, str(postid))
                        
                if removed_tags:
                    Tag.remove_postid_from_tags(removed_tags, str(postid))                
            
            clear_cache_by_pathlist(cache_key_list)
            rspd['status'] = 200
            rspd['msg'] = '完成： 你已经成功编辑了一篇文章 <a href="/t/%s" target="_blank">查看编辑后的文章</a>' % str(postid)
            self.write(json.dumps(rspd))
            return
        else:
            rspd['status'] = 500
            rspd['msg'] = '错误： 未知错误，请尝试重新提交'
            self.write(json.dumps(rspd))
            return            

class DelPost(BaseHandler):
    @authorized()
    def get(self, id = ''):
        Article.del_post_by_id(id)
        clear_cache_by_pathlist(['post:%s'%id])
        self.redirect('%s/admin/edit_post/'% (BASE_URL))
    
class EditComment(BaseHandler):
    @authorized()
    def get(self, id = ''):
        obj = None
        if id:
            obj = Comment.get_comment_by_id(id)
            if obj:
                act = self.get_argument("act",'')
                if act == 'del':
                    Comment.del_comment_by_id(id)
                    clear_cache_by_pathlist(['post:%d'%obj.postid])
                    self.redirect('%s/admin/comment/'% (BASE_URL))
                    return
        self.echo('admin_comment.html', {
            'title': "管理评论",
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_all_tag_name(),
            'obj': obj,
            'comments': Comment.get_recent_comments(),
        },layout='_layout_admin.html')        
    
    @authorized()
    def post(self, id = ''):
        act = self.get_argument("act",'')
        if act == 'findid':
            eid = self.get_argument("id",'')
            self.redirect('%s/admin/comment/%s'% (BASE_URL, eid))
            return
        
        tf = {'true':1,'false':0}
        post_dic = {
            'author': self.get_argument("author"),
            'email': self.get_argument("email"),
            'content': safe_encode(self.get_argument("content").replace('\r','\n')),
            'url': self.get_argument("url",''),
            'visible': self.get_argument("visible",'false'),
            'id': id
        }
        post_dic['visible'] = tf[post_dic['visible'].lower()]
        
        Comment.update_comment_edit(post_dic)
        clear_cache_by_pathlist(['post:%s'%id])
        self.redirect('%s/admin/comment/%s'% (BASE_URL, id))
        return

class LinkBroll(BaseHandler):
    @authorized()
    def get(self):
        act = self.get_argument("act",'')
        id = self.get_argument("id",'')
        
        obj = None
        if act == 'del':
            if id:
                Link.del_link_by_id(id)
                clear_cache_by_pathlist(['/'])
            self.redirect('%s/admin/links'% (BASE_URL))
            return
        elif act == 'edit':
            if id:
                obj = Link.get_link_by_id(id)
                clear_cache_by_pathlist(['/'])
        self.echo('admin_link.html', {
            'title': "管理友情链接",
            'objs': Link.get_all_links(),
            'obj': obj,
        },layout='_layout_admin.html')        
        
    @authorized()
    def post(self):
        act = self.get_argument("act",'')
        id = self.get_argument("id",'')
        name = self.get_argument("name",'')
        sort = self.get_argument("sort",'0')
        url = self.get_argument("url",'')
        
        if name and url:
            params = {'id': id, 'name': name, 'url': url, 'displayorder': sort}
            if act == 'add':
                Link.add_new_link(params)
            
            if act == 'edit':
                Link.update_link_edit(params)
            
            clear_cache_by_pathlist(['/'])
            
        self.redirect('%s/admin/links'% (BASE_URL))
        return

class FlushData(BaseHandler):
    @authorized()
    def get(self):
        act = self.get_argument("act",'')
        if act == 'flush':
            MyData.flush_all_data()
            clear_all_cache()
            self.redirect('/admin/flushdata')
            return
        elif act == 'flushcache':
            clear_all_cache()
            self.redirect('/admin/flushdata')
            return
        
        self.echo('admin_flushdata.html', {
            'title': "清空缓存/数据",
        },layout='_layout_admin.html')

class PingRPCTask(BaseHandler):
    def get(self):
        for n in range(len(XML_RPC_ENDPOINTS)):
            add_task('default', '%s/task/pingrpc/%d' % (BASE_URL, n))
        self.write(str(time()))
    
    post = get
    
class PingRPC(BaseHandler):
    def get(self, n = 0):
        import urllib2
        
        pingstr = self.render('rpc.xml', {'article_id':Article.get_max_id()})
        
        headers = {
            'User-Agent':'request',
            'Content-Type' : 'text/xml',
            'Content-length' : str(len(pingstr))
        }
        
        req = urllib2.Request(
            url = XML_RPC_ENDPOINTS[int(n)],
            headers = headers,
            data = pingstr,
        )
        try:
            content = urllib2.urlopen(req).read()
            tip = 'Ping ok' + content
        except:
            tip = 'ping erro'
            
        self.write(str(time()) + ": " + tip)
        #add_task('default', '%s/task/sendmail'%BASE_URL, urlencode({'subject': tip, 'content': tip + " " + str(n)}))
        
    post = get

class SendMail(BaseHandler):
    def post(self):
        subject = self.get_argument("subject",'')
        content = self.get_argument("content",'')
        
        if subject and content:
            sae.mail.send_mail(NOTICE_MAIL, subject, content,(MAIL_SMTP, int(MAIL_PORT), MAIL_FROM, MAIL_PASSWORD, True))

class Install(BaseHandler):
    def get(self):
        try:
            self.write('如果出现错误请尝试刷新本页。')
            has_user = User.check_has_user()
            if has_user:
                self.write('博客已经成功安装了，你可以直接 <a href="/admin/flushdata">清空网站数据</a>')
            else:
                self.write('博客数据库已经建立，现在就去 <a href="/admin/">设置一个管理员帐号</a>')
        except:
            MyData.creat_table()
            self.write('博客已经成功安装了，现在就去 <a href="/admin/">设置一个管理员帐号</a>')

class NotFoundPage(BaseHandler):
    def get(self):
        self.set_status(404)
        self.echo('error.html', {
            'page': '404',
            'title': "Can't find out this URL",
            'h2': 'Oh, my god!',
            'msg': 'Something seems to be lost...'
        })

#####
urls = [
    (r"/admin/", HomePage),
    (r"/admin/login", Login),
    (r"/admin/logout", Logout),
    (r"/admin/403", Forbidden),
    (r"/admin/add_post", AddPost),
    (r"/admin/edit_post/(\d*)", EditPost),
    (r"/admin/del_post/(\d+)", DelPost),
    (r"/admin/comment/(\d*)", EditComment),
    (r"/admin/flushdata", FlushData),
    (r"/task/pingrpctask", PingRPCTask),
    (r"/task/pingrpc/(\d+)", PingRPC),
    (r"/task/sendmail", SendMail),
    (r"/install", Install),
    (r"/admin/fileupload", FileUpload),
    (r"/admin/links", LinkBroll),
    (r".*", NotFoundPage)
]
