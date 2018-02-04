#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Yihang Ding'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from coroweb import get, post

from aiohttp import web

from config import configs

from models import User, Comment, Blog, next_id

from apis import APIValueError, APIResourceNotFoundError, APIPermissionError,APIError, Page

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 0:
		p = 1
	return p

def user2cookie(user, max_age):
	'''
	Generate cookie str by user.
	'''
	# build cookie string by: id-expires-sha1
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

async def cookie2user(cookie_str):
	'''
	Parse cookie and load user if cookie is valid.
	'''
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

def text2html(text):
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-z]{40}$')

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

@get('/')  # the main page
async def index(*, page='1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	page = Page(num, page_index)
	# num is the # of items
	if num == 0:
		blogs = []
	else:
		blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
	return {
			'__template__':'blogs.html',
			'page':page,
			'blogs':blogs
	}

@get('/blog/{id}') # the specific blog with id {id}
async def get_blog(id):
	blog = await Blog.find(id)
	comments = await Comment.findAll('blog_id=?',[id],orderBy='created_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
			'__template__':'blog.html',
			'blog':blog,
			'comments': comments
	}

@get('/register')  # register a new user
def register():
	return {
	'__template__': 'register.html'
	}

@get('/signin')  # signin
def signin():
	return {
	'__template__': 'signin.html'
	}

@get('/signout') #signout
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age = 0, httponly=True)
	logging.info('user signed out.')
	return r

@get('/manage/') # manage by Administrator
def manage():
	return 'redirect: /manage/blogs'

@get('/manage/blogs/create') #create a new blog
def manage_create_blog():
	return {
			'__template__': 'manage_blog_edit.html',
			'id': '',
			'action':'/api/blogs'
	}

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
	return {
			'__template__':'manage_blog_edit.html',
			'id': id,
			'action':'/api/blogs/%s' % id
	}

@get('/manage/blogs')  # manage blogs existed
async def manage_blogs(*, page = '1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	page = Page(num, page_index)
	if page_index > page.page_count:
		page_index = page_index -1 
	return {
			'__template__': 'manage_blogs.html',
			'page_index': page_index,
			'page_count': page.page_count,
			'item_count': page.item_count
	}

@get('/manage/comments')   # manage all comments
async def manage_comments(*, page = '1'):
	page_index = get_page_index(page)
	num = await Comment.findNumber('count(id)')
	page = Page(num, page_index)
	if page_index > page.page_count:
		page_index = page_index -1 
	return {
			'__template__':'manage_comments.html',
			'page_index': page_index,
			'page_count': page.page_count,
			'item_count': page.item_count
	}

@get('/manage/users')  # manage all users
async def manage_users(*, page='1'):
	page_index = get_page_index(page)
	num = await User.findNumber('count(id)')
	page = Page(num, page_index)
	if page_index > page.page_count:
		page_index = page_index -1 
	return {
			'__template__':'manage_users.html',
			'page_index': page_index,
			'page_count': page.page_count,
			'item_count': page.item_count
	}

@get('/author')
def index_author():
	return {'__template__': 'author.html'}

@get('/study')
def index_study():
	return {'__template__': 'study.html'}

#=================================API===================================

@post('/api/users')  # api for registering a new user
async def api_register_user(*,email, name, passwd):
	# email, name, paawd are required for registaration
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email=?', [email])
	if len(users) > 0:
		raise APIError('register: failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	user = User(
		id = uid,
		# id is not necessarily assigned since the default value of 'id' is next_id()
		name = name.strip(),
		email = email,
		passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
		image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest()
		)
	await user.save()
	# make session cookie:
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400,httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/api/authenticate')  # api for verification
async def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid password.')
	users = await User.findAll('email=?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	# check passwd
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid password!')
	# set cookie
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	logging.info('%s: sign in and generate cookies successfully.' % user.name)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body =json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/api/blogs/{id}') # api for getting a specific blog
async def api_get_blog(*, id):
	blog = await Blog.find(id)
	return blog

@post('/api/blogs/{id}')  # api for updating a blog
async def api_update_blog(id, request,*, name, summary, content):
	check_admin(request)
	blog = await Blog.find(id)
	if not name or not name.strip():
		raise APIValueError('name','name cannot be empty.')
	if not name or not summary.strip():
		raise APIValueError('summary','summary cannot be empty.')
	if not name or not name.strip():
		raise APIValueError('content','content cannot be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip()
	blog.content = content.strip()
	await blog.update()
	return blog

@post('/api/blogs/{id}/delete') # api for deleting a blog
async def api_delete_blog(request, *, id):
	check_admin(request)
	blog = await Blog.find(id)
	await blog.remove()
	comments = await Comment.findAll('blog_id=?',[id])
	for comment in comments:
		await comment.remove()
	return dict(id=id)

@post('/api/blogs')  # api for creating a new blog
async def api_create_blog(request, *, name, summary, content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog = Blog(user_id=request.__user__.id, 
				user_name=request.__user__.name,
				user_image=request.__user__.image,
				name=name.strip(),
				summary=summary.strip(),
				content=content.strip()
				)
	await blog.save()
	return blog

@get('/api/blogs') # api for management of blogs
async def api_blogs(*, page = '1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, blogs=())
	blogs = await Blog.findAll(orderBy='created_at desc', limit = (p.offset, p.limit))
	return dict(page=p, blogs=blogs)

@get('/api/comments') # api for management of comments
async def api_comments(*, page = '1'):
	page_index = get_page_index(page)
	num = await Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	for comment in comments:
		# 找对应的文章
		id = comment.blog_id
		blog = await Blog.find(id)
		comment['blog_name'] = blog.name
	return dict(page=p, comments=comments)

@post('/api/comments/{id}/delete') # api for deleting a comment
async def api_delete_comments(id, request):
	check_admin(request)
	c = await Comment.find(id)
	if c is None:
		raise APIResourceNotFoundError('Comment')
	await c.remove()
	return dict(id=id)

@post('/api/users/{id}/delete') # api for deleting an user
async def api_delete_users(id, request):
	check_admin(request)
	id_buff = id
	user = await User.find(id)
	if user is None:
		raise APIResourceNotFoundError('Comment')
	await user.remove()
	# 给被删除的用户在评论中标记
	comments = await Comment.findAll('user_id=?',[id])
	if comments:
		for comment in comments:
			id = comment.id
			c = await Comment.find(id)
			c.user_name = c.user_name + ' (该用户已被删除)'
			await c.update()
	id = id_buff
	return dict(id=id)


@post('/api/blogs/{id}/comments')  # api for creating a comment in for a specific blog
async def api_create_comment(id, request, *, content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = await Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id = blog.id, user_id = user.id, user_name=user.name, user_image=user.image, content=content.strip())
	await comment.save()
	return comment

@get('/api/users')   # api for management of users
async def api_get_users(*, page='1'):
	page_index = get_page_index(page)
	num = await User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	for u in users:
		u.passwd = '******'
	return dict(page=p, users=users)