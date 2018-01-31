#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Yihang Ding'

import asyncio, os, inspect, logging, functools

from urllib import parse
from aiohttp import web
from apis import APIError

def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

# fn中不带缺省值的强制关键字参数为函数的输出
def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	'''
	'params' here is an OrderedDict consisting info of parameters of fn,
	i.e., OrderDict{'a': <Parameter "a">, ...} 
	where a is one of parameters of fn.
	'''
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
		# when 'name' is KEYWORD_ONLY and 'name' has no default value
		# 也就是不带缺省值的强制关键字参数为函数的输出
			args.append(name)
	return tuple(args)

# fn中强制关键字参数为函数的输出
def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
		# when 'name' is KEYWORD_ONLY
		# 也就是强制关键字参数为函数的输出
			args.append(name)
	return tuple(args)

# fn的参数中是否含有关键字参数？
def has_named_kw_args(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if para.kind == inspect.Parameter.KEYWORD_ONLY:
			return True
			# this function is similr to the last one

#fn的参数中是否含有**kw
def has_var_kw_arg(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			# 'VAR_KEYWORD' actually is **kw
			# 也就是寻找关键字参数（dict）
			return True

#fn的参数中是否含有'request'参数且为最后一个（不考虑*args和**kw在内）
def has_request_arg(fn):
	params = inspect.signature(fn).parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in the function: %s%s' % (fn.__name__, str(inspect.signature(fn))))
	return found
			# this is used to find whether 'request' is a parameter of fn.
			# VAR_POSITIONAL: *args, which depends on position to make input
			# KEYWORD_ONLY: must use keyword to make input rather than position
			# VAR_KEYWORD: **kw, which depends on keyword to make input
			# once 'request' is found, no other parameter except from '*args' and '**kw' is allowed to locate.

class RequestHandler(object):

	'''
	1. Analyze the parameters of fn(request handler function)
	2. Retrieve info or kw from request
	3. Call fn with input kw and get output as 'web.Request'
	'''

	def __init__(self, app, fn):
		self._app = app
		self._func = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	async def __call__(self, request):
		'''
		Instance of RequestHandler is callable.
		For exampple:
		handler1 = RequestHander(app1, fn1)
		handler1(request1)
		'''
		kw = None
		if self._has_var_kw_arg or sef._has_named_kw_args or self._required_kw_args:
			# if fn has parameters like **kw or KEYWORD_ONLY(with or without default value)
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content_type')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = await request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest('JSON body must be an object.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = await request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]
		if kw == None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				# if fn does not have **kw and fn has KEYWORD_ONLY
				# remove all unamed kw
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			# check named arg:
			for k, v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicte arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._has_request_arg:
			kw['request'] = request
		# check required kw:
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest('Missing argument: %s' % name)
		logging.info('call with args: %s' % str(kw))
		try:
			r = await self._func(**kw)
			# self._func is input 'fn'
			return r
		except APIError as e:
			return dict(error = e.error, data = e.data, message = e.message)


def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s'%('/static/', path))

def add_route(app, fn):
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % fn.__name__)
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method, path, RequestHandler(app, fn))
	# please note that 'RequestHandler(app, fn)' here is callable. 
	# Thus it acts like a faction (in fact an instance).

def add_routes(app, module_name):
	''' 
	'module_name' is another module consisting url handlers.
	
	Please note that 'module_name' might also be in the form of
	'package.module'. In this case, we need to retrieve the 
	name of module we want (module_name[n+1:]) and set 'fromlist' 
	in __import__ function as the name of module.

	__import__(name, globals=None, locals=None, fromlist=(), level=0)
	when name = package.module:
	if fromlist is not assigned, then we return packge; else we will
	return package.fromlist
	'''
	n = module_name.rfind('.')
	if n == (-1):
		# not found in 'module_name'
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), local(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
