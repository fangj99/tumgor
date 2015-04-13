# -*- coding: utf-8 -*-

import cgi
import wsgiref.handlers
import os
import simplejson
import urllib
import hashlib
import datetime
import re

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import users

BASE = 'http://a.sadpast.com'
TOPIC_PAGE = 20
REPLY_PAGE = 50

class Topic(db.Model):
    author = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    title = db.StringProperty()
    content = db.TextProperty()
    t = db.ListProperty(str)
    reply = db.ListProperty(int)
    status = db.StringProperty()

class T(db.Model):
    name = db.StringProperty()
    description = db.StringProperty()
    topic = db.ListProperty(int)
    status = db.StringProperty()

class Reply(db.Model):
    author = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    topic = db.StringProperty()
    content = db.TextProperty()
    to = db.ListProperty(int)
    status = db.StringProperty()

class Index(db.Model):
    index = db.ListProperty(int)
    name = db.ListProperty(str)


def init(self):
    cache = memcache.get('cache')
    if cache and cache.has_key('system'):
        system = cache['system']
    else:
        try:
            result = urlfetch.fetch(BASE + '/json', method=urlfetch.POST, headers={'Content-Type': 'application/json'}, deadline=10)
            if result.status_code == 200:
                system = simplejson.decoder.JSONDecoder().decode(result.content)
                if cache:
                    cache['system'] = system
                else:
                    cache = {'system': system}
                memcache.set('cache', cache)
            else:
                system = None
        except:
            system = None
    return system

def admin():
    if users.is_current_user_admin():
        return True

def error(self):
    template_values = {
        'base': BASE
    }
    path = os.path.join(os.path.dirname(__file__), '../template/error.html')
    self.response.out.write(template.render(path, template_values))

def current(self):
    if self.request.cookies and self.request.cookies.get('user') and self.request.cookies.get('session'):
        username = self.request.cookies.get('user')
        user = memcache.get(username)
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

def login(self):
    url = self.request.url
    
    rt = self.request.get('rt').strip()
    if rt:
        self.response.headers.add_header('Set-Cookie', 'public="true"; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
        self.redirect(BASE + '/user/login?rt=' + rt)
        return
    at = self.request.get('at').strip()
    if at:
        result = urlfetch.fetch(BASE + '/user/login?at=' + at, headers={'Content-Type': 'application/json'}, deadline=10)
        if result.status_code == 200:
            user = simplejson.decoder.JSONDecoder().decode(result.content)
            username = user['username']
            
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
            
            self.response.headers.add_header('Set-Cookie', 'public=""; expires=' + datetime.datetime.now().strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
            
            all_users = get_all_users()
            if all_users and all_users.name:
                if username not in all_users.name:
                    all_users.name.append(username)
                    all_users.put()
                    memcache.set('all_users', all_users)
            else:
                all_users = Index(key_name='all_users')
                all_users.name = [username]
                all_users.put()
                memcache.set('all_users', all_users)
            
            if len(url.split('?at')) > 1:
                self.redirect(url.split('?at')[0])
                return
            if len(url.split('&at')) > 1:
                self.redirect(url.split('&at')[0])
                return
    public = self.request.get('public').strip()
    if public:
        self.response.headers.add_header('Set-Cookie', 'public="true"; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
        if len(url.split('?public')) > 1:
            self.redirect(url.split('?public')[0])
            return
        if len(url.split('&public')) > 1:
            self.redirect(url.split('&public')[0])
            return

def is_mobile(self):
	user_agent = self.request.headers['User-Agent']
	if (re.search('iPod|iPhone|Android|Opera Mini|BlackBerry|webOS|UCWEB|Blazer|PSP|Symbian|IEMobile', user_agent)):
		return True
	else:
		return None

def get_recent_topic():
    cache = memcache.get('recent_topic')
    if not cache:
        return get_topic_page(1)
    else:
        return cache

def get_topic(id):
    cache = memcache.get('topic' + str(id))
    if not cache:
        topic = Topic.get_by_id(id)
        if topic:
            memcache.set('topic' + str(id), topic)
            return topic
        else:
            return None
    else:
        return cache

def get_topic_page(page):
    all_topics = get_all_topics()
    if all_topics:
        topic_page_id = all_topics.index[TOPIC_PAGE*(page-1):TOPIC_PAGE*page]
        topic_page = []
        for item in topic_page_id:
            topic_page.append(get_topic(item))
        return topic_page
    else:
        return None

def get_all_topics():
    cache = memcache.get('all_topics')
    if not cache:
        all_topics = Index.get_by_key_name('all_topics')
        if all_topics:
            memcache.set('all_topics', all_topics)
            return all_topics
        else:
            return None
    else:
        return cache

def get_topics(topic_ids, page):
    topic_id = topic_ids[TOPIC_PAGE*(page-1):TOPIC_PAGE*page]
    if topic_id:
        topics = []
        for item in topic_id:
            topics.append(get_topic(item))
        return topics

def get_t(name):
    cache = memcache.get('t' + name)
    if not cache:
        t = T.all().filter("name = ", name).get()
        if t:
            memcache.set('t' + name, t)
            return t
        else:
            return None
    else:
        return cache

def get_all_ts():
    cache = memcache.get('all_ts')
    if not cache:
        all_ts = Index.get_by_key_name('all_ts')
        if all_ts:
            memcache.set('all_ts', all_ts)
            return all_ts
        else:
            return None
    else:
        return cache

def get_reply(id):
    cache = memcache.get('reply' + str(id))
    if not cache:
        reply = Reply.get_by_id(id)
        if reply:
            memcache.set('reply' + str(id), reply)
            return reply
        else:
            return None
    else:
        return cache

def get_reply_page(topic, page):
    reply_page_id = None
    if len(topic.reply) < REPLY_PAGE * (page - 1):
        return None
    if len(topic.reply) < REPLY_PAGE * page:
        reply_page_id = topic.reply[0:len(topic.reply) - REPLY_PAGE * (page - 1)]
    else:
        reply_page_id = topic.reply[len(topic.reply) - REPLY_PAGE * page:len(topic.reply) - REPLY_PAGE * (page - 1)]
    reply_page = []
    for item in reply_page_id:
        reply_page.append(get_reply(item))
    return reply_page

def get_hot_t():
    all_ts = get_all_ts()
    if all_ts:
        hot_t_id = all_ts.name[:10]
        hot_t = []
        for item in hot_t_id:
            hot_t.append(item)
        return hot_t
    else:
        return None

def get_none_read_notify(username):
    none_read_notify = 0
    if username:
        notifyuser = memcache.get(username)
        if notifyuser and notifyuser.has_key('notify'):
            notify = notifyuser['notify']
            if notify:
                for item in notify:
                    if item['status'] == '1':
                        none_read_notify += 1
    return none_read_notify

def get_all_users():
    cache = memcache.get('all_users')
    if not cache:
        all_users = Index.get_by_key_name('all_users')
        if all_users:
            memcache.set('all_users', all_users)
            return all_users
        else:
            return None
    else:
        return cache