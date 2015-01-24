#!/usr/bin/env python
# encoding: utf-8

from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/proxies")
def get_proxies():
    try:
        from pymongo import MongoClient
        client = MongoClient('58.218.248.114')
        db = client['proxy_db']
        proxy_collection = db['proxies']
    except:
        return 'error'
    html = ''
    for proxy in proxy_collection.find():
        ip = proxy['ip']
        port = proxy['port']
        p = '<p>%s:%s</p>' % (ip,port)
        html += p
    return html


if __name__ == "__main__":
    app.run(host='0.0.0.0')
