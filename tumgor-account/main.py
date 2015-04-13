# -*- coding: utf-8 -*-

import cgi
import wsgiref.handlers
import os
import re
import hashlib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from module import *
from module import user_module


class Main(webapp.RequestHandler):
    def get(self, string):
        system = init(self)
        if not system:
            return
        
        user = user_module.current(self)
        if user and user.has_key('user'):
            user = user['user']
        template_values = {
            'system': system,
            'user': user,
            'mobile': is_mobile(self)
        }
        
        if string in ['about']:
            template_values['page'] = string
        else:
            if len(string) >= 6 and len(string) <= 30 and re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(string):
                showuser = user_module.get(str(string.lower()))
                if showuser and showuser.has_key('user'):
                    showuser = showuser['user']
                    if showuser:
                        template_values['showuser'] = showuser
                        path = os.path.join(os.path.dirname(__file__), 'template/user.html')
                        self.response.out.write(template.render(path, template_values))
                        return
                    else:
                        self.redirect('/')
                        return
                else:
                    self.redirect('/')
                    return
            elif len(string) >= 6 and len(string) <= 30 and re.compile(r"(?:^[a-zA-Z0-9]+\/avatar$)", re.IGNORECASE).match(string):
                username = string.split('/avatar')[0]
                showuser = user_module.get(str(username.lower()))
                if showuser and showuser.has_key('user'):
                    showuser = showuser['user']
                    if showuser:
                        email = showuser.email
                        s = self.request.get('s').strip()
                        if email:
                            if s:
                                self.redirect('http://www.gravatar.com/avatar/' + hashlib.new('md5', str(email)).hexdigest() + '?d=mm&s=' + s)
                            else:
                                self.redirect('http://www.gravatar.com/avatar/' + hashlib.new('md5', str(email)).hexdigest() + '?d=mm')
                        else:
                            if s:
                                self.redirect('http://www.gravatar.com/avatar/00000000000000000000000000000000?d=mm&s=' + s)
                            else:
                                self.redirect('http://www.gravatar.com/avatar/00000000000000000000000000000000?d=mm')
                        return
                    else:
                        self.redirect('/')
                        return
                else:
                    self.redirect('/')
                    return
            elif string:
                self.redirect('/')
                return
            else:
                template_values['page'] = 'home'
        path = os.path.join(os.path.dirname(__file__), 'template/' + template_values['page'] + '.html')
        self.response.out.write(template.render(path, template_values))

class Admin(webapp.RequestHandler):
    def get(self):
        if admin():
            config(self)
        else:
            self.redirect(users.create_login_url('/'))
    def post(self):
        if admin():            
            name = self.request.get('name').strip()
            description = self.request.get('description').strip()
            email = self.request.get('email').strip()
            
            system = get(self)
            
            if name and re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE).match(email):
                if not system:
                    system = System(key_name='system')
                
                system.name = name
                system.description = description
                system.email = email
                
                system.put()
                
                cache = memcache.get('cache')
                if not cache:
                    cache = {'system': system}
                else:
                    if cache.has_key('system'):
                        cache['system'] = system
                memcache.set('cache', cache)
            else:
                template_values = {
                    'system': system,
                    'name': name,
                    'description': description,
                    'email': email,
                    'mobile': is_mobile(self)
                }
                if not re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE).match(email):
                    template_values['error'] = '2'
                if not name:
                    template_values['error'] = '1'
                path = os.path.join(os.path.dirname(__file__), 'template/config.html')
                self.response.out.write(template.render(path, template_values))
                return
            self.redirect('/admin')
        else:
            self.redirect('/')

class Json(webapp.RequestHandler):
    def post(self, string):
        system = init(self)
        if not system:
            return
        
        system = '{"name": "%s", "description": "%s", "email": "%s"}' % (system.name, system.description, system.email)
        
        self.response.headers.add_header('content-type', 'application/json', charset='utf-8')
        self.response.out.write(system)


application = webapp.WSGIApplication([
    ('/admin', Admin),
    ('/json(.*)', Json),
    ('/(.*)', Main)
], debug=True)

def main():
    template.register_template_library('templatetags.timezone')
    template.register_template_library('templatetags.urltolink')
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()