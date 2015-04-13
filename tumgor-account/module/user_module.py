# -*- coding: utf-8 -*-

from google.appengine.ext import db

from google.appengine.api import memcache

import hashlib
import datetime

class User(db.Model):
    username = db.StringProperty()
    password = db.StringProperty()
    email = db.StringProperty()
    realname = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    other = db.TextProperty()

def get(username):
    if not username:
        return None
    user = memcache.get(username)
    if not user:
        user = User.get_by_key_name(str(username.lower()))
        if user:
            user = {
                'user': user
            }
            memcache.set(username, user)
    return user

def current(self):
    if self.request.cookies and self.request.cookies.get('user') and self.request.cookies.get('session'):
        username = self.request.cookies.get('user')
        user = get(username)
        if user and user.has_key('user') and user.has_key('session'):
            session = user['session']
            if session and session == self.request.cookies.get('session'):
                return user
            else:
                return None
        else:
            return None
    else:
        return None

def oauth(self):
    oauth = None
    f = self.request.get('f').strip().encode('utf-8')
    if f:
        if current(self):
            rt = hashlib.new('md5', str(datetime.datetime.now()) + self.request.remote_addr).hexdigest()
            memcache.set(rt, f, time=60)
            if len(f.split('?')) > 1:
                self.redirect(f + '&rt=' + rt)
            else:
                self.redirect(f + '?rt=' + rt)
            oauth = True
        else:
            if self.request.get('public').strip():
                if len(f.split('?')) > 1:
                    self.redirect(f + '&public=true')
                else:
                    self.redirect(f + '?public=true')
                oauth = True
    rt = self.request.get('rt').strip()
    if rt:
        f = memcache.get(rt)
        if f:
            user = current(self)
            if user and user.has_key('user'):
                user = user['user']
                if user:
                    username = user.username
                    at = hashlib.new('md5', str(datetime.datetime.now()) + self.request.remote_addr).hexdigest()
                    
                    memcache.set(at, username, time=10)
                    memcache.delete(rt)
                    if len(f.split('?')) > 1:
                        self.redirect(f + '&at=' + at)
                    else:
                        self.redirect(f + '?at=' + at)
                    oauth = True
    at = self.request.get('at').strip()
    if at:
        username = memcache.get(at)
        if username and get(username):
            user = get(username)
            if user.has_key('user'):
                user = user['user']
                if user and user.username:
                    json = '{"username": "%s"' % (user.username)
                    if user.realname:
                        json += ', "realname": "%s"' % (user.realname)
                    if user.email:
                        json += ', "email": "%s"' % (user.email)
                    json += '}'
                    memcache.delete(at)
                    self.response.headers.add_header('content-type', 'application/json', charset='utf-8')
                    self.response.out.write(json)
                    oauth = True
    return oauth