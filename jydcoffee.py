#!/usr/bin/env python
#
# (c) 2013 Joost Yervante Damad <joost@damad.be>
# License: GPL

import os.path
import re
import string

import PyV8

supported_formats = ['1.0']

class Global(PyV8.JSClass):

    def __init__(self):
      self.path = ""

    def require(self, arg):
      content = ""
      with open(self.path+arg+".js") as file:
        file_content = file.read()
      result = None
      try:
        store_path = self.path
        self.path = self.path + os.path.dirname(arg) + "/"
        result = PyV8.JSContext.current.eval(file_content)
      finally:
        self.path = store_path
      return result

js_make_js_from_coffee = None
js_make_js_ctx = None

def prepare_coffee_compiler():
  global js_make_js_from_coffee
  global js_make_js_ctx
  if js_make_js_from_coffee == None:
      js_make_js_ctx = PyV8.JSContext(Global())
      js_make_js_ctx.enter()
      try:
        js_make_js_from_coffee = js_make_js_ctx.eval("""
(function (coffee_code) {
  CoffeeScript = require('coffee-script/coffee-script');
  js_code = CoffeeScript.compile(coffee_code, {bare:true});
  return js_code;
})
""")
      finally:
        js_make_js_ctx.leave()

# there is probably plenty of room for speeding up things here by
# re-using the generated js from ground and such, however for now it is
# still snappy enough; so let's just keep it simple
def eval_coffee_footprint(coffee):
  meta = eval_coffee_meta(coffee)
  if 'format' not in meta:
    raise Exception("Missing mandatory #format meta field")
  else:
    format = meta['format']
  if format not in supported_formats:
     raise Exception("Unsupported file format. Supported formats: %s" % (supported_formats))
  # only compile the compiler once
  global js_make_js_ctx
  global js_make_js_from_coffee
  if js_make_js_ctx == None:
    prepare_coffee_compiler()
  try:
    js_make_js_ctx.enter()
    with open("grind/ground-%s.coffee" % (format)) as f: ground = f.read()
    ground_js = js_make_js_from_coffee(ground)
    js = js_make_js_from_coffee(coffee + "\nreturn footprint()\n")
    with PyV8.JSContext() as ctxt:
      pl = PyV8.convert(ctxt.eval("(function() {\n" + ground_js + js + "\n}).call(this);\n"))
      pl.append(meta)
      return pl
  finally:
    js_make_js_ctx.leave()

def eval_coffee_meta(coffee):
  lines = coffee.replace('\r', '').split('\n')
  meta_lines = filter(lambda c: re.match('^#\w+',c), lines)
  meta_list = map(lambda c: re.split('\s',c, 1), meta_lines)
  meta_list = map(lambda c: (c[0][1:], c[1]), meta_list)
  meta = {}
  for (k,v) in meta_list:
    if k in meta:
      meta[k] = meta[k] + "\n" + v
    else:
      meta[k] = v
  meta['type'] = 'meta'
  return meta