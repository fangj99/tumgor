# -*- coding: utf-8 -*-

import cgi
import wsgiref.handlers
import os
import re
import hashlib
import datetime

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import mail

from module import *
from module import user_module


class Main(webapp.RequestHandler):
    def get(self, string):
        self.redirect('/')

class Register(webapp.RequestHandler):
    def get(self):
        system = init(self)
        if not system:
            return
        
        if user_module.current(self):
            self.redirect('/')
            return
        
        template_values = {
            'system': system,
            'captcha': captcha(),
            'mobile': is_mobile(self)
        }
        path = os.path.join(os.path.dirname(__file__), 'template/register.html')
        self.response.out.write(template.render(path, template_values))
    def post(self):
        system = init(self)
        if not system:
            return
        
        if user_module.current(self):
            self.redirect('/')
            return
        
        username = self.request.get('username').strip()
        password = self.request.get('password')
        result = self.request.get('captcha')
        
        cache = memcache.get('cache')
        if not (cache and cache.has_key('captcha') and str(cache['captcha']) == result):
            template_values = {
                'system': system,
                'captcha': captcha(),
                'username': username,
                'mobile': is_mobile(self),
                'error': '5'
            }
            path = os.path.join(os.path.dirname(__file__), 'template/register.html')
            self.response.out.write(template.render(path, template_values))
            return
        
        if not (len(username) >= 6 and len(username) <= 30 and re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(username) and password):
            template_values = {
                'system': system,
                'captcha': captcha(),
                'username': username,
                'mobile': is_mobile(self)
            }
            if not password:
                template_values['error'] = '3'
            if not re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(username):
                template_values['error'] = '2'
            if not (len(username) >= 6 and len(username) <= 30):
                template_values['error'] = '1'
            path = os.path.join(os.path.dirname(__file__), 'template/register.html')
            self.response.out.write(template.render(path, template_values))
        else:
            if not user_module.get(username) and not user_module.get(str(username.lower())):
                password = hashlib.new('md5', password).hexdigest()
                user = user_module.User(key_name=str(username.lower()))
                user.username = username
                user.password = password
                user.put()
                
                session = hashlib.new('md5', str(datetime.datetime.now())).hexdigest()
                self.response.headers.add_header('Set-Cookie', 'user=' + str(username) + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
                self.response.headers.add_header('Set-Cookie', 'session=' + session + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
                
                cache = {
                    'user': user,
                    'session': session
                }
                memcache.set(username, cache)
                
                cache = memcache.get('cache')
                if cache and cache.has_key('captcha'):
                    del cache['captcha']
                    memcache.set('cache', cache)
                
                template_values = {
                    'system': system,
                    'user': user,
                    'register': True,
                    'mobile': is_mobile(self)
                }
                path = os.path.join(os.path.dirname(__file__), 'template/settings.html')
                self.response.out.write(template.render(path, template_values))
            else:
                template_values = {
                    'system': system,
                    'captcha': captcha(),
                    'username': username,
                    'mobile': is_mobile(self),
                    'error': '4'
                }
                path = os.path.join(os.path.dirname(__file__), 'template/register.html')
                self.response.out.write(template.render(path, template_values))

class Login(webapp.RequestHandler):
    def get(self):
        system = init(self)
        if not system:
            return
        
        if user_module.oauth(self):
            return
        
        if user_module.current(self):
            self.redirect('/')
            return
        
        template_values = {
            'system': system
        }
        path = os.path.join(os.path.dirname(__file__), 'template/login.html')
        self.response.out.write(template.render(path, template_values))
    def post(self):
        system = init(self)
        if not system:
            return
        
        if user_module.current(self):
            self.redirect('/')
            return
        
        username = self.request.get('username').strip()
        password = self.request.get('password')
        
        if not (len(username) >= 6 and len(username) <= 30 and re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(username) and password):
            template_values = {
                'system': system,
                'username': username,
                'mobile': is_mobile(self)
            }
            if not password:
                template_values['error'] = '3'
            if not re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(username):
                template_values['error'] = '2'
            if not (len(username) >= 6 and len(username) <= 30):
                template_values['error'] = '1'
            path = os.path.join(os.path.dirname(__file__), 'template/login.html')
            self.response.out.write(template.render(path, template_values))
        else:
            user = user_module.get(username)
            if user and user.has_key('user'):
                user = user['user']
                if user.password == hashlib.new('md5', password).hexdigest():
                    session = hashlib.new('md5', str(datetime.datetime.now())).hexdigest()
                    
                    cache = memcache.get(username)
                    if not cache:
                        cache = {
                            'user': user,
                            'session': session
                        }
                    else:
                        cache['user'] = user
                        if cache.has_key('session'):
                            session = cache['session']
                        else:
                            cache['session'] = session
                    memcache.set(username, cache)
                    
                    self.response.headers.add_header('Set-Cookie', 'user=' + str(username) + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
                    self.response.headers.add_header('Set-Cookie', 'session=' + str(session) + '; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
                    
                    cache = memcache.get('cache')
                    if cache and cache.has_key('reset'):
                        reset = cache['reset']
                        if reset.has_key(username):
                            del reset[username]
                            cache['reset'] = reset
                            memcache.set('cache', cache)
                    
                    #授权跳转
                    f = self.request.get('f').strip()
                    if f:
                        self.redirect('/user/login?f=' + f)
                        return
                    
                    self.redirect('/')
                else:
                    template_values = {
                        'system': system,
                        'username': username,
                        'mobile': is_mobile(self),
                        'error': '5'
                    }
                    path = os.path.join(os.path.dirname(__file__), 'template/login.html')
                    self.response.out.write(template.render(path, template_values))
            else:
                template_values = {
                    'system': system,
                    'username': username,
                    'mobile': is_mobile(self),
                    'error': '4'
                }
                path = os.path.join(os.path.dirname(__file__), 'template/login.html')
                self.response.out.write(template.render(path, template_values))

class Logout(webapp.RequestHandler):
    def get(self):
        user = user_module.current(self)
        if user and user.has_key('user') and user.has_key('session'):
            username = user['user'].username
            del user['session']
            memcache.set(username, user)
            
            self.response.headers.add_header('Set-Cookie', 'user=""; expires=' + datetime.datetime.now().strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
            self.response.headers.add_header('Set-Cookie', 'session=""; expires=' + datetime.datetime.now().strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
        self.redirect('/user/login')

class Settings(webapp.RequestHandler):
    def get(self):
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
            path = os.path.join(os.path.dirname(__file__), 'template/settings.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/user/login')
    def post(self):
        system = init(self)
        if not system:
            return
        
        user = user_module.current(self)
        if user and user.has_key('user'):
            user = user['user']
            username = self.request.get('username').strip()
            if username == user.username:
                realname = self.request.get('realname').strip()
                email = self.request.get('email').strip()
                other = self.request.get('other')
                
                password = self.request.get('password')
                password1 = self.request.get('password1')
                password2 = self.request.get('password2')
                
                type = self.request.get('type')
                
                register = self.request.get('register')
                
                settings = None
                if type == 'info':
                    if realname and realname != user.realname:
                        user.realname = realname
                        settings = True
                    if not email or (re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE).match(email) and email != user.email):
                        user.email = email
                        settings = True
                    if other != user.other:
                        user.other = other
                        settings = True
                    if email and not re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE).match(email):
                        template_values = {
                            'system': system,
                            'user': user,
                            'email': email,
                            'mobile': is_mobile(self),
                            'error': '4'
                        }
                        if register:
                            template_values['register'] = True
                        path = os.path.join(os.path.dirname(__file__), 'template/settings.html')
                        self.response.out.write(template.render(path, template_values))
                        return
                if type == 'password' and (password or password1 or password2):
                    if password and password1 and password2 and password1 == password2 and password != password1 and hashlib.new('md5', password).hexdigest() == user.password:
                        user.password = hashlib.new('md5', password1).hexdigest()
                        settings = True
                    else:
                        template_values = {
                            'system': system,
                            'user': user,
                            'mobile': is_mobile(self)
                        }
                        if password == password1:
                            template_values['error'] = '3'
                        if not password1 or password1 != password2:
                            template_values['error'] = '2'
                        if not password or hashlib.new('md5', password).hexdigest() != user.password:
                            template_values['error'] = '1'
                        path = os.path.join(os.path.dirname(__file__), 'template/settings.html')
                        self.response.out.write(template.render(path, template_values))
                        return
                if settings:
                    user.put()
                    
                    cache = memcache.get(username)
                    if not cache:
                        cache = {'user': user}
                    else:
                        cache['user'] = user
                    memcache.set(username, cache)
                
                if not register:
                    self.redirect('/user/settings')
                else:
                    self.redirect('/')
            else:
                self.redirect('/user/settings')
        else:
            self.redirect('/user/login')

class Profile(webapp.RequestHandler):
    def get(self):
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
            path = os.path.join(os.path.dirname(__file__), 'template/profile.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/user/login')

class Forgot(webapp.RequestHandler):
    def get(self):
        system = init(self)
        if not system:
            return
        template_values = {
            'system': system
        }
        path = os.path.join(os.path.dirname(__file__), 'template/forgot.html')
        self.response.out.write(template.render(path, template_values))
    def post(self):
        system = init(self)
        if not system:
            return
        
        username = self.request.get('username').strip()
        email = self.request.get('email').strip()
        
        if not (len(username) >= 6 and len(username) <= 30 and re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(username) and re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE).match(email)):
            template_values = {
                'system': system,
                'username': username,
                'email': email,
                'mobile': is_mobile(self)
            }
            if not re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)", re.IGNORECASE).match(email):
                template_values['error'] = '3'
            if not re.compile(r"(?:^[a-zA-Z0-9]+$)", re.IGNORECASE).match(username):
                template_values['error'] = '2'
            if not (len(username) >= 6 and len(username) <= 30):
                template_values['error'] = '1'
            path = os.path.join(os.path.dirname(__file__), 'template/forgot.html')
            self.response.out.write(template.render(path, template_values))
        else:
            user = user_module.get(username)
            if user and user.has_key('user'):
                user = user['user']
                if user.email == email:
                    password = user.password
                    
                    key = hashlib.new('md5', (username + password)).hexdigest()
                    reset = {username: key}
                    
                    cache = memcache.get('cache')
                    if not cache:
                        cache = {
                            'reset': reset
                        }
                    else:
                        if cache.has_key('reset'):
                            cache['reset'][username] = key
                        else:
                            cache['reset'] = reset
                    memcache.set('cache', cache)
                    
                    url = self.request.host_url + '/user/reset/' + key
                    
                    resetmail = mail.EmailMessage()
                    resetmail.sender = system.email
                    resetmail.subject = '重置密码'
                    resetmail.to = email
                    resetmail.body = u'重置密码，请访问网址： (%s)' % (url)
                    resetmail.html = u'重置密码，请访问网址：<br /> <a href="(%s)">(%s)</a>' % (url, url)
                    resetmail.send()
                    
                    template_values = {
                        'system': system,
                        'error': '0'
                    }
                    path = os.path.join(os.path.dirname(__file__), 'template/forgot.html')
                    self.response.out.write(template.render(path, template_values))
                else:
                    template_values = {
                        'system': system,
                        'username': username,
                        'email': email,
                        'mobile': is_mobile(self),
                        'error': '5'
                    }
                    path = os.path.join(os.path.dirname(__file__), 'template/forgot.html')
                    self.response.out.write(template.render(path, template_values))
            else:
                template_values = {
                    'system': system,
                    'username': username,
                    'email': email,
                    'mobile': is_mobile(self),
                    'error': '4'
                }
                path = os.path.join(os.path.dirname(__file__), 'template/forgot.html')
                self.response.out.write(template.render(path, template_values))

class Reset(webapp.RequestHandler):
    def get(self, key):
        system = init(self)
        if not system:
            return
        cache = memcache.get('cache')
        if cache and cache.has_key('reset'):
            reset = cache['reset']
            if key in reset.values():
                template_values = {
                    'system': system
                }
                path = os.path.join(os.path.dirname(__file__), 'template/reset.html')
                self.response.out.write(template.render(path, template_values))
            else:
                self.redirect('/')
        else:
            self.redirect('/')
    def post(self, key):
        system = init(self)
        if not system:
            return
        
        password1 = self.request.get('password1')
        password2 = self.request.get('password2')
        if not (password1 and password2 and password1 == password2):
            template_values = {
                'system': system,
                'mobile': is_mobile(self),
                'error': '1'
            }
            path = os.path.join(os.path.dirname(__file__), 'template/reset.html')
            self.response.out.write(template.render(path, template_values))
        else:
            cache = memcache.get('cache')
            if cache and cache.has_key('reset'):
                reset = cache['reset']
                username = None
                for k, v in reset.items():
                    if v == key:
                        username = k
                if username:
                    user = user_module.get(username)
                    if user and user.has_key('user'):
                        user = user['user']
                        user.password = hashlib.new('md5', password1).hexdigest()
                        user.put()

                        cache = memcache.get(username)
                        if not cache:
                            cache = {'user': user}
                        else:
                            cache['user'] = user
                        memcache.set(username, cache)
                        
                        cache = memcache.get('cache')
                        if cache and cache.has_key('reset'):
                            reset = cache['reset']
                            for k, v in reset.items():
                                if v == key:
                                    del reset[v]
                            cache['reset'] = reset
                            memcache.set('cache', cache)
                        
                        template_values = {
                            'system': system,
                            'mobile': is_mobile(self),
                            'error': '0'
                        }
                        path = os.path.join(os.path.dirname(__file__), 'template/reset.html')
                        self.response.out.write(template.render(path, template_values))
                    else:
                        self.redirect('/')
                else:
                    self.redirect('/')
            else:
                self.redirect('/')


application = webapp.WSGIApplication([
    ('/user/register', Register),
    ('/user/login', Login),
    ('/user/logout', Logout),
    ('/user/forgot', Forgot),
    ('/user/reset/(.*)', Reset),
    ('/user/settings', Settings),
    ('/user/profile', Profile),
    ('/user(.*)', Main)
], debug=True)

def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()