# -*- coding: utf-8 -*-
from os import environ

SAEPY_LOG_VERSION = '0.0.1' # 当前SAEpy-log版本
APP_NAME = environ.get("APP_NAME", "")
debug = not APP_NAME

##下面需要修改
SITE_TITLE = u"博客标题" #博客标题
SITE_TITLE2 = u"博客标题2" #显示在边栏上头
SITE_SUB_TITLE = u"副标题" #副标题
KEYWORDS = u"吃饭，睡觉，工作" #博客关键字
SITE_DECR = u"又一款SAEpy-log 博客" #博客描述
ADMIN_NAME = "Admin" #发博文的作者
NOTICE_MAIL = "xxxxxx@qq.com" #常用的，容易看到的接收提醒邮件，如QQ 邮箱，仅作收件用

###配置邮件发送信息，提醒邮件用的，必须正确填写
MAIL_FROM = 'xxxxxx@gmail.com'
MAIL_SMTP = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_PASSWORD = 'xxxxxx'

GOOGLE_ANALYTICS_ID = '' #Google Analytics ID，不用就留空
GOOGLE_CSE_ID = '' #Google自定义搜索引擎ID，不用就留空

#使用SAE Storage 服务（保存上传的附件），需在SAE管理面板创建
STORAGE_DOMAIN_NAME = 'attachment' 

####友情链接列表，在管理后台也实现了管理，下面的链接列表仍然有效并排在前面
LINK_BROLL = [
    {"text": 'SAEpy blog', "url": 'http://saepy.sinaapp.com'},
    {"text": 'Sina App Engine', "url": 'http://sae.sina.com.cn/'},
]

###设置容易调用的jquery 文件
JQUERY = "http://lib.sinaapp.com/js/jquery/1.6.2/jquery.min.js"
#JQUERY = "http://code.jquery.com/jquery-1.6.2.min.js"

COPY_YEAR = '2011' #页脚的 © 2011 

#当发表新博文时自动ping RPC服务，中文的下面三个差不多了
XML_RPC_ENDPOINTS = [
    'http://blogsearch.google.com/ping/RPC2', 
    'http://rpc.pingomatic.com/', 
    'http://ping.baidu.com/ping/RPC2'
]

MAJOR_DOMAIN = '%s.sinaapp.com' % APP_NAME #主域名，默认是SAE 的二级域名

##如果要在本地测试则需要配置Mysql 数据库信息
if debug:
    MYSQL_DB = 'app_saepy'
    MYSQL_USER = 'root'
    MYSQL_PASS = '123'
    MYSQL_HOST_M = '127.0.0.1'
    MYSQL_HOST_S = '127.0.0.1'
    MYSQL_PORT = '3306'

############## 下面不建议修改 ###########################

if debug:
    BASE_URL = 'http://127.0.0.1:8080'
else:
    BASE_URL = 'http://%s'%MAJOR_DOMAIN
    
LANGUAGE = 'zh-CN'
THEMES = ['default','admin']

COMMENT_DEFAULT_VISIBLE = 1 #0/1 #发表评论时是否显示 设为0时则需要审核才显示
EACH_PAGE_POST_NUM = 10 #每页显示文章数
EACH_PAGE_COMMENT_NUM = 10 #每页评论数
RELATIVE_POST_NUM = 5 #显示相关文章数
SHORTEN_CONTENT_WORDS = 150 #文章列表截取的字符数
DESCRIPTION_CUT_WORDS = 100 #meta description 显示的字符数
RECENT_COMMENT_NUM = 5 #边栏显示最近评论数
RECENT_COMMENT_CUT_WORDS = 20 #边栏评论显示字符数
LINK_NUM = 20 #边栏显示的友情链接数
MAX_COMMENT_NUM_A_DAY = 10 #客户端设置Cookie 限制每天发的评论数

##以下是pyTenjin 模板引擎对页面片段的缓存时间，
DEFAULT_TENJIN_CACHE = 3600
ARTICLE_LIST_TENJIN_CACHE = 3600
SIDER_TENJIN_CACHE = 3600
ARTICLE_TENJIN_CACHE = 3600
ARTICLE_COMMENT_TENJIN_CACHE = 3600

HOT_TAGS_NUM = 100 #右侧热门标签显示数

MAX_IDLE_TIME = 5 #数据库最大空闲时间 SAE文档说是30 其实更小，设为5，没问题就不要改了

