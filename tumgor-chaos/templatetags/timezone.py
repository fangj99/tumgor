# -*- coding: utf-8 -*-

from google.appengine.ext.webapp import template
from datetime import timedelta

register = template.create_template_register()
@register.filter

def timezone(value,offset):
    return value + timedelta(hours=offset)