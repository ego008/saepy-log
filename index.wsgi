import sae
import tornado.wsgi

from blog import urls as blogurls
from admin import urls as adminurls

settings = { 
    'debug': True,
}

app = tornado.wsgi.WSGIApplication(blogurls + adminurls, **settings)

application = sae.create_wsgi_app(app)

















