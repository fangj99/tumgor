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

from datetime import timedelta

from module import *


class Main(webapp.RequestHandler):
    def get(self, string):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user and not self.request.cookies.get('public'):
            self.redirect(BASE + '/user/login?public=true&f=' + url)
            return
        
        hot_t = get_hot_t()
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        template_values = {
            'system': system,
            'user': user,
            'base': BASE,
            'url': url,
            'topics': get_recent_topic(),
            'hot_t': hot_t,
            'mobile': is_mobile(self)
        }
        if get_topic_page(2):
            template_values['next_page'] = 2
        
        path = os.path.join(os.path.dirname(__file__), 'template/home.html')
        self.response.out.write(template.render(path, template_values))

class Logout(webapp.RequestHandler):
    def get(self):
        user = current(self)
        if user and user.has_key('user') and user.has_key('session'):
            username = user['user']['username']
            del user['session']
            memcache.set(username, user)
            
            self.response.headers.add_header('Set-Cookie', 'public="true"; expires=' + (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
            
            self.response.headers.add_header('Set-Cookie', 'user=""; expires=' + datetime.datetime.now().strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
            self.response.headers.add_header('Set-Cookie', 'session=""; expires=' + datetime.datetime.now().strftime("%a, %d-%b-%Y %H:%M:%S GMT") + '; path=/')
            
            f = self.request.get('f')
            if f:
                self.redirect(f)
                return
        self.redirect('/')

class CreateTopic(webapp.RequestHandler):
    def get(self):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        
        if not user and not self.request.cookies.get('public'):
            self.redirect(BASE + '/user/login?f=' + url)
            return
        
        hot_t = get_hot_t()
        
        t = self.request.get('t').strip()
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        template_values = {
            'system': system,
            'user': user,
            'base': BASE,
            'url': url,
            'hot_t': hot_t,
            'at': t,
            'mobile': is_mobile(self)
        }
        
        path = os.path.join(os.path.dirname(__file__), 'template/createtopic.html')
        self.response.out.write(template.render(path, template_values))
    def post(self):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user:
            self.redirect(BASE + '/user/login?f=' + url)
            return
        
        title = self.request.get('title').strip()
        content = self.request.get('content').strip()
        ts = self.request.get_all('t')
        for item in ts:
            if not item:
                ts.remove(item)
        addt = self.request.get('addt').strip()

        hot_t = get_hot_t()
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        if addt:
            
            template_values = {
                'system': system,
                'user': user,
                'base': BASE,
                'url': url,
                'title': title,
                'content': content,
                'hot_t': hot_t,
                't': ts,
                'mobile': is_mobile(self)
            }
            path = os.path.join(os.path.dirname(__file__), 'template/createtopic.html')
            self.response.out.write(template.render(path, template_values))
            return
        if title and len(title) < 140 and ts:
            error = None
            for item in ts:
                if len(item) > 30 or re.search(r'\~|\`|\!|\@|\#|\$|\%|\^|\&|\*|\(|\)|\_|\-|\+|\=|\{|\}|\[|\]|\||\\|\:|\;|\"|\'|\<|\>|\,|\.|\?|\/', item) or not re.match(ur'[a-zA-Z0-9\u4e00-\u9fa5]+', item):
                    error = True
            if not error:
                if user.has_key('username'):
                    username = user['username']
                    if username:
                        topic = Topic()
                        
                        topic.author = username
                        topic.title = title
                        topic.content = content
                        
                        ts = list(set(ts))
                        
                        topic.t = ts
                        
                        topic.put()
                        
                        id = topic.key().id()
                        memcache.set('topic' + str(id), topic)
                        
                        all_topics = get_all_topics()
                        if all_topics and id not in all_topics.index:
                            all_topics.index.insert(0, id)
                        else:
                            all_topics = Index(key_name='all_topics')
                            all_topics.index = [id]
                        all_topics.put()
                        memcache.set('all_topics', all_topics)
                        
                        for item in ts:
                            t = get_t(item)
                            if t and id not in t.topic:
                                t.topic.insert(0, id)
                            else:
                                t = T()
                                t.name = item
                                t.topic = [id]
                            t.put()
                            memcache.set('t' + item, t)
                        
                        all_ts = get_all_ts()
                        if all_ts:
                            for item in ts:
                                if item not in all_ts.name:
                                    all_ts.name.append(item)
                            all_ts.name = list(set(all_ts.name))
                            all_ts.name.sort(key=lambda x:len(get_t(x).topic), reverse=True)
                        else:
                            all_ts = Index(key_name='all_ts')
                            all_ts.name = ts
                        
                        all_ts.put()
                        memcache.set('all_ts', all_ts)
                        
                        recent_topic = get_topic_page(1)
                        memcache.set('recent_topic', recent_topic)
                        
                        hot_t = get_hot_t()
                        memcache.set('hot_t', hot_t)
                self.redirect('/')
            else:
                template_values = {
                    'system': system,
                    'user': user,
                    'base': BASE,
                    'url': url,
                    'title': title,
                    'content': content,
                    'hot_t': hot_t,
                    't': ts,
                    'mobile': is_mobile(self)
                }
                template_values['error'] = '3'
                path = os.path.join(os.path.dirname(__file__), 'template/createtopic.html')
                self.response.out.write(template.render(path, template_values))
        else:
            template_values = {
                'system': system,
                'user': user,
                'base': BASE,
                'url': url,
                'title': title,
                'content': content,
                'hot_t': hot_t,
                't': ts,
                'mobile': is_mobile(self)
            }
            if not ts:
                template_values['error'] = '2'
            if not title:
                template_values['error'] = '1'
            path = os.path.join(os.path.dirname(__file__), 'template/createtopic.html')
            self.response.out.write(template.render(path, template_values))

class ReadTopic(webapp.RequestHandler):
    def get(self, string):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user and not self.request.cookies.get('public'):
            self.redirect(BASE + '/user/login?public=true&f=' + url)
            return
        
        to = self.request.get('to').strip()
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        if re.compile(r"(?:^([0-9]+)$)", re.IGNORECASE).match(string):
            topic = get_topic(int(string))
            if topic:
                replies = get_reply_page(topic, 1)
                
                template_values = {
                    'system': system,
                    'user': user,
                    'base': BASE,
                    'url': url,
                    'topic': topic,
                    'replies': replies,
                    'to': to,
                    'mobile': is_mobile(self)
                }
                
                if get_reply_page(topic, 2):
                    template_values['next_page'] = '2'
                
                path = os.path.join(os.path.dirname(__file__), 'template/topic.html')
                self.response.out.write(template.render(path, template_values))
            else:
                self.redirect('/')
        elif re.compile(r"(?:^([0-9]+)\/p\/([0-9]+)$)", re.IGNORECASE).match(string):
            id = long(string.split('/p/')[0])
            page = int(string.split('/p/')[1])
            topic = get_topic(id)
            if topic and page > 0:
                replies = get_reply_page(topic, page)
                
                template_values = {
                    'system': system,
                    'user': user,
                    'base': BASE,
                    'url': url,
                    'topic': topic,
                    'replies': replies,
                    'mobile': is_mobile(self)
                }
                
                if get_reply_page(topic, int(page) + 1):
                    template_values['next_page'] = int(page) + 1
                if get_reply_page(topic, int(page) - 1):
                    template_values['prev_page'] = int(page) - 1
                
                path = os.path.join(os.path.dirname(__file__), 'template/topic.html')
                self.response.out.write(template.render(path, template_values))
            else:
                self.redirect('/')
        else:
            self.redirect('/')
    def post(self, string):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user:
            self.redirect(BASE + '/user/login?f=' + url)
            return
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        if re.compile(r"(?:^([0-9]+)$)", re.IGNORECASE).match(string):
            id = string
        elif re.compile(r"(?:^([0-9]+)\/p\/([0-9]+)$)", re.IGNORECASE).match(string):
            id = string.split('/p/')[0]
        else:
            self.redirect('/')
            return
        
        content = self.request.get('content').strip()
        if content:
            if user.has_key('username'):
                username = user['username']
                if username:
                    topic = get_topic(long(id))
                    if topic:
                        reply = Reply()
                        reply.author = username
                        reply.content = content
                        reply.topic = id
                        reply.put()
                        
                        reply_id = reply.key().id()
                        
                        memcache.set('reply' + str(reply_id), reply)
                        
                        topic.reply.append(reply_id)
                        topic.put()
                        memcache.set('topic' + id, topic)
                        
                        for item in topic.t:
                            t = get_t(item)
                            if t:
                                if long(id) in t.topic:
                                    t.topic.remove(long(id))
                                t.topic.insert(0, long(id))
                                t.put()
                                memcache.set('t' + item, t)
                        
                        all_topics = get_all_topics()
                        if all_topics:
                            if long(id) in all_topics.index:
                                all_topics.index.remove(long(id))
                            all_topics.index.insert(0, long(id))
                            all_topics.put()
                            memcache.set('all_topics', all_topics)
                        
                        recent_topic = get_topic_page(1)
                        memcache.set('recent_topic', recent_topic)
                        
                        #提醒
                        memtioned = re.findall(r'@[a-zA-Z0-9]+', content)
                        memtioned = list(set(memtioned))
                        for item in memtioned:
                            memtioned[memtioned.index(item)] = item.lstrip('@')
                        if not len(memtioned):
                            user = memcache.get(str(topic.author))
                            if user:
                                if user.has_key('notify'):
                                    user['notify'].insert(0, {
                                        'type': 'topic',
                                        'author': username,
                                        'topic': id,
                                        'reply': str(reply.key().id()),
                                        'status': '1'
                                    })
                                else:
                                    user['notify'] = [{
                                        'type': 'topic',
                                        'author': username,
                                        'topic': id,
                                        'reply': str(reply.key().id()),
                                        'status': '1'
                                    }]
                            else:
                                user = {
                                    'notify': [{
                                        'type': 'topic',
                                        'author': username,
                                        'topic': id,
                                        'reply': str(reply.key().id()),
                                        'status': '1'
                                    }]
                                }
                            memcache.set(str(topic.author), user)
                        else:
                            all_users = get_all_users()
                            for item in memtioned:
                                if all_users and item in all_users.name:
                                    user = memcache.get(item)
                                    if user:
                                        if user.has_key('notify'):
                                            user['notify'].insert(0, {
                                                'type': 'reply',
                                                'author': username,
                                                'topic': id,
                                                'reply': str(reply.key().id()),
                                                'status': '1'
                                            })
                                        else:
                                            user['notify'] = [{
                                                'type': 'reply',
                                                'author': username,
                                                'topic': id,
                                                'reply': str(reply.key().id()),
                                                'status': '1'
                                            }]
                                    else:
                                        user = {
                                            'notify': [{
                                                'type': 'reply',
                                                'author': username,
                                                'topic': id,
                                                'reply': str(reply.key().id()),
                                                'status': '1'
                                            }]
                                        }
                                    memcache.set(item, user)
        self.redirect('/topic/' + id)

class Notify(webapp.RequestHandler):
    def get(self):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user and not self.request.cookies.get('public'):
            self.redirect(BASE + '/user/login?public=true&f=' + url)
            return
        
        if user:
            user['none_read_notify'] = '0'
        
        if user:
            username = user['username']
            notifyuser = memcache.get(username)
            notify = None
            if notifyuser and notifyuser.has_key('notify'):
                notify = notifyuser['notify']
                if notify:
                    for item in notifyuser['notify']:
                        item['status'] = '0'
                    memcache.set(username, notifyuser)
                    for item in notify:
                        item['topic'] = get_topic(long(item['topic']))
                        item['reply'] = get_reply(long(item['reply']))
            template_values = {
                'system': system,
                'user': user,
                'base': BASE,
                'url': url,
                'notify': notify,
                'mobile': is_mobile(self)
            }
            path = os.path.join(os.path.dirname(__file__), 'template/notify.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/')
            return

class TopicPage(webapp.RequestHandler):
    def get(self, page):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user and not self.request.cookies.get('public'):
            self.redirect(BASE + '/user/login?public=true&f=' + url)
            return
        
        hot_t = get_hot_t()
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        template_values = {
            'system': system,
            'user': user,
            'base': BASE,
            'url': url,
            'topics': get_topic_page(int(page)),
            'hot_t': hot_t,
            'page': int(page),
            'mobile': is_mobile(self)
        }
        if get_topic_page(int(page)+1):
            template_values['next_page'] = int(page) + 1
        if get_topic_page(int(page)-1):
            template_values['prev_page'] = int(page) - 1
        
        path = os.path.join(os.path.dirname(__file__), 'template/home.html')
        self.response.out.write(template.render(path, template_values))
    def post(self):
        return

class TPage(webapp.RequestHandler):
    def get(self, string):
        system = init(self)
        if not system:
            error(self)
            return
        
        login(self)
        user = current(self)
        if user and user.has_key('user'):
            user = user['user']
        else:
            user = None
        url = self.request.url
        if not user and not self.request.cookies.get('public'):
            self.redirect(BASE + '/user/login?public=true&f=' + url)
            return
        
        if user:
            user['none_read_notify'] = str(get_none_read_notify(user['username']))
        
        name = string
        page = 1
        if re.compile(r"(?:^(.*)\/p\/([0-9]+)$)", re.IGNORECASE).match(string):
            name = string.split('/p/')[0]
            page = string.split('/p/')[1]
        
        name = urllib.unquote(name)
        name = name.decode('utf-8')
        
        t = get_t(name)
        if t:
            topic_ids = t.topic
            topics = get_topics(topic_ids, int(page))
            
            template_values = {
                'system': system,
                'user': user,
                'base': BASE,
                'url': url,
                't': name,
                'topics': topics,
                'mobile': is_mobile(self)
            }
            if get_topics(topic_ids, int(page) + 1):
                template_values['next_page'] = int(page) + 1
            if get_topics(topic_ids, int(page) - 1):
                template_values['prev_page'] = int(page) - 1
            
            path = os.path.join(os.path.dirname(__file__), 'template/t.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/')
    def post(self, string):
        return

class Json(webapp.RequestHandler):
    def get(self, string):
        host = self.request.host_url
        recent_topic = get_recent_topic()
        hot_t = get_hot_t()
        json = 'chaos({topics: ['
        i = 0
        for topic in recent_topic:
            if i != 0:
                json += ', '
            json += '{"author": "' + topic.author + '", "title": "' + topic.title + '", "created": "' + str((topic.created + timedelta(hours=+8)).strftime('%Y-%m-%d %H:%M:%S')).encode('utf-8') + '", "id": "' + str(topic.key().id()) + '", "reply": "' + str(len(topic.reply)) + '"}'
            i += 1
        json += '], ts: ['
        i = 0
        for t in hot_t:
            if i !=0:
                json += ', '
            json += '{"name": "' + t + '"}'
            i += 1
        json += ']'
        if get_topic_page(2):
            json += ', "more": "true"'
        else:
            json += ', "more": ""'
        
        none_read_notify = None
        if string:
            none_read_notify = str(get_none_read_notify(string))
        if none_read_notify:
            json += ', "notify": "' + none_read_notify + '"'
        else:
            json += ', "notify": ""'
        
        json += '})'
        self.response.headers.add_header('content-type', 'application/json', charset='utf-8')
        self.response.out.write(json)

class Admin(webapp.RequestHandler):
    def get(self):
        if admin():
            system = init(self)
            if not system:
                error(self)
                return
            
            template_values = {
                'system': system,
                'base': BASE,
                'mobile': is_mobile(self)
            }
            path = os.path.join(os.path.dirname(__file__), 'template/config.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect(users.create_login_url('/admin'))
    def post(self):
        if admin():
            dbr = self.request.get('dbr')
            if dbr:
                all_topics = Index.get_by_key_name('all_topics')
                if all_topics:
                    all_topics.index = list(set(all_topics.index))
                    all_topics.index.sort(key=lambda x:Topic.get_by_id(x).updated, reverse=True)
                    all_topics.put()
                    memcache.set('all_topics', all_topics)
                    
                    for item in all_topics.index:
                        topic = Topic.get_by_id(item)
                        if topic:
                            topic.reply = list(set(topic.reply))
                            topic.reply.sort(key=lambda x:Reply.get_by_id(x).created, reverse=False)
                            topic.put()
                            memcache.set('topic' + str(item), topic)
                
                all_ts = Index.get_by_key_name('all_ts')
                if all_ts:
                    all_ts.name = list(set(all_ts.name))
                    all_ts.name.sort(key=lambda x:len(T.all().filter("name = ", x).get().topic), reverse=True)
                    all_ts.put()
                    memcache.set('all_ts', all_ts)
                    
                    for item in all_ts.name:
                        t = T.all().filter("name = ", item).get()
                        if t:
                            t.topic = list(set(t.topic))
                            t.topic.sort(key=lambda x:Topic.get_by_id(x).updated, reverse=False)
                            t.put()
                            memcache.set('t' + item, t)
        self.redirect('/admin')


application = webapp.WSGIApplication([
    ('/logout', Logout),
    ('/topic/create', CreateTopic),
    ('/topic/(.*)', ReadTopic),
    ('/p/(.*)', TopicPage),
    ('/t/(.*)', TPage),
    ('/notify', Notify),
    ('/json/(.*)', Json),
    ('/admin', Admin),
    ('/(.*)', Main)
], debug=True)

def main():
    template.register_template_library('templatetags.timezone')
    template.register_template_library('templatetags.urltolink')
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()