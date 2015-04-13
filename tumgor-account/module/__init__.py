# -*- coding: utf-8 -*-

import os
import random
import re

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from google.appengine.api import memcache
from google.appengine.api import users

class System(db.Model):
    name = db.StringProperty()
    description = db.StringProperty()
    email = db.EmailProperty()

def get(self):
    cache = memcache.get('cache')
    if cache and cache.has_key('system'):
        system = cache['system']
    else:
        system = None
    if not system:
        system = System.all().get()
        if system:
            if not cache:
                cache = {'system': system}
            else:
                cache['system'] = system
            memcache.set('cache', cache)
    return system

def init(self):
    system = get(self)
    if not system:
        if admin():
            self.redirect('/admin')
        else:
            error(self)
    return system

def error(self):
    template_values = {
        'mobile': is_mobile(self)
    }
    path = os.path.join(os.path.dirname(__file__), '../template/error.html')
    self.response.out.write(template.render(path, template_values))

def admin():
    if users.is_current_user_admin():
        return True

def config(self):
    system = get(self)
    
    template_values = {
        'system': system,
        'mobile': is_mobile(self)
    }
    path = os.path.join(os.path.dirname(__file__), '../template/config.html')
    self.response.out.write(template.render(path, template_values))

def captcha():
    captcha = {
        'number1': random.randint(0,9),
        'number2': random.randint(0,9),
        'operate': random.randint(0,9)
    }
    
    if captcha['operate']:
        result = captcha['number1'] + captcha['number2']
    else:
        result = captcha['number1'] - captcha['number2']
    
    cache = memcache.get('cache')
    if cache:
        cache['captcha'] = result
    else:
        cahce = {'captcha': result}
    memcache.set('cache', cache)
    
    return captcha

def is_mobile(self):
	user_agent = self.request.headers['User-Agent']
	if (re.search('iPod|iPhone|Android|Opera Mini|BlackBerry|webOS|UCWEB|Blazer|PSP|Symbian|IEMobile', user_agent)):
		return True
	else:
		return None