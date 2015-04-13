# -*- coding: utf-8 -*-

from google.appengine.ext.webapp import template
import re
import cgi

register = template.create_template_register()
@register.filter

def urltolink(value):
    html = re.sub(ur'(?P<url>http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),(|)]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)', lambda m: '<a href="' + m.group('url') + '" target="_blank">' + m.group('url') + '</a>', value)
    return html