SAEpy-log 是一款运行在SAE/python上轻型的、性能卓越的blog程序

示例 http://saepy.sinaapp.com

说明
SAEpy-log 是 SAE python blog的简写，是学习使用SAE 的生成物。
没有设计得很复杂，能写点博客就行。

性能
页面响应一般少于150毫秒，平均在60毫秒左右，已缓存页面响应常在3~6毫秒；
一般博客只需使用1M缓存即可；

已实现的功能：

生成ATOM供稿
XML-RPC ping
生成网站地图
可在配置文件中更换使用主题
邮件通知
代码高亮
富文本编辑器
AJAX表单
缓存页面
密码保护
基于tag的相关文章
附件上传

安装方法：
1）下载最新源码；
2）修改 /config.yaml 把 name: saepy 改为自己的；
3）修改 setting.py 的相关设置
4）到SAE 后台开通相关服务（mysql/Storage/Memcache/Task Queue）

# 1 初始化 Mysql
# 2 建立一个名为 attachment 的 Storage
# 3 启用Memcache，初始化大小为1M的 mc，大小可以调，日后文章多了，PV多了可增加
# 4 创建一个 名为 default 的 Task Queue
# 详见 http://saepy.sinaapp.com/t/50 详细安装指南

5)打包程序，在SAE 后台通过打包上传代码；
6）打开 http://your_app_id.sinaapp.com/install 如果出错刷新两三次就可以

版权
SAEpy-log程序主体以MIT许可发布。

另外还使用到了下列不属于本程序的库或资源：
kuwata-lab.com的[Tenjin]( http://www.kuwata-lab.com/tenjin/ )模板引擎（做了一些修改以适应SAE），（MIT License）
[jQuery]( http://jquery.com/ ) （MIT License）
Facebox （MIT License）
jquery.cookie （MIT License）
[jQuery.upload]( http://lagoscript.org ) （MIT License）
[markItUp!]( http://markitup.jaysalvat.com/home/ ) （MIT License）
[Highlight.js]( http://softwaremaniacs.org/soft/highlight/en/ ) （BSD license）
[octopress]( http://www.octopress.org/ )主题 （从WordPress移植过来）
其他属于Python或Tornado或Sina App Engine自带的库
