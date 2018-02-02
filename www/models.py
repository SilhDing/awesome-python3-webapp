#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = 'Yihang Ding'

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
	return '%015d%s000' % (int(time.time())*1000, uuid.uuid4().hex)

class User(Model):
	__table__ = 'users'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(150)')
	# only primary_key of 'id' is 'True'
	email = StringField(ddl = 'varchar(50)')
	passwd = StringField(ddl = 'varchar(50)')
	admin = BooleanField()
	name = StringField(ddl = 'varchar(50)')
	image = StringField(ddl = 'varchar(500)')
	created_at = FloatField(default = time.time)

class Blog(Model):
	__table__ = 'blogs'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(150)')
	user_id = StringField(ddl = 'varchar(50)')
	user_name = StringField(ddl = 'varchar(50)')
	user_image = StringField(ddl = 'varchar(500)')
	name = StringField(ddl = 'varchar(50)')
	summary = StringField(ddl = 'varchar(200)')
	content = TextField()
	created_at = FloatField(default = time.time)

class Comment(Model):
	__table__ = 'comments'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(150)')
	blog_id = StringField(ddl = 'varchar(50)')
	user_id = StringField(ddl = 'varchar(50)')
	user_name = StringField(ddl = 'varchar(50)')
	user_image = StringField(ddl = 'varchar(500)')
	content = TextField()
	created_at = FloatField(default = time.time)

# --------------  test code  --------------
# this piece of code is used to make all variables visible in the orm.py
'''
yihang = User(
	email = 'test@test.com', 
	passwd = '19940811',
	name = 'Yihang Ding',
	)
# print(dir(yihang))
print('yihang dict:\n', yihang)
inner = yihang.__mapping__

print('\n------contents in __mapping__ (name, column_type, primary_key, default)------')
for k in inner:
	v = inner[k]
	value = v.default() if callable(v.default) else v.default
	print('%s: %s, %s, %s, %s' % (k, v.name, v.column_type, v.primary_key, value))

print('\n------others------')
print('__table__: %s' % yihang.__table__)
print('__primary_key__: %s' % yihang.__primary_key__)
print('__fields__: %s' % yihang.__fields__)

args = list(map(yihang.getValueOrDefault, yihang.__fields__))
args.append(yihang.getValueOrDefault(yihang.__primary_key__))
print(args)
'''
