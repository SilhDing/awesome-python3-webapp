#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Yihang Ding'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
	logging.info('*** start to handler request by index()...')
	users = await User.findAll()
	logging.info('~~~~~~ %s'% users)
	return {'__template__': 'test.html','users': users}
