#coding:utf-8
"""
author @yuzt
created on 2014.8.20
"""
import traceback
import threading
import re
import pymongo
import time
import requests
try:
    import PyV8
    from bs4 import BeautifulSoup
except ImportError:
    print "Import Error"


headers ={
    "Host": "www.xici.net.co",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.99 Safari/537.36",
    "Referer": "http://www.xici.net.co/nn/",
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
}

threadLock = threading.Lock()
ThreadNum = 50

def getIPs_proxy_ru():
    IPs = []
    proxy_types = ['gaoni','niming']
    for proxy_type in proxy_types:
        proxy_url = 'http://proxy.com.ru/%s' % (proxy_type,)
        r = requests.get(proxy_url)
        soup = BeautifulSoup(r.content.decode('gbk'))
        html = str(soup)
        pattern = re.compile('共(\d+)页')
        total_page_num = int(pattern.findall(html)[0])
        for i in range(min(20,total_page_num)):
            url = 'http://proxy.com.ru/%s/list_%s.html' % (proxy_type,i+1,)
            r = requests.get(url)
            soup = BeautifulSoup(r.content)
            table = soup.findAll('table')[7]
            trs = table.findAll('tr')
            for tr in trs[1:]:
                tds = tr.findAll('td')
                ip = tds[1].text.strip()
                port = tds[2].text.strip()
                IPs.append(ip+':'+port)
    return IPs

def getIPs_proxy_digger():
    with open('aes.js') as f:
        jsaes = f.read()
    with open('pad.js') as f:
        pad = f.read()

    socket_list = []
    url = 'http://www.site-digger.com/html/articles/20110516/proxieslist.html'
    r = requests.get(url)
    soup = BeautifulSoup(r.content)
    definition = ''
    scripts = soup.find_all('script')
    for script in scripts:
        if 'baidu_union_id' in script.text:
            definition = script.text
    #print definition
    for tr in soup.find_all('tr'):
        if 'script' in str(tr):
            tds = tr.findAll('td')
            proxy_type = tds[1].text
            if proxy_type == 'Anonymous' :#and location == 'China':
                with PyV8.JSContext() as ctxt:
                    ctxt.eval(jsaes)
                    ctxt.eval(pad)
                    ctxt.eval(definition)
                    command = tds[0].script.text[15:-2]
                    #print command
                    socket_addres = ctxt.eval(command)
                    socket_list.append(socket_addres)
    return socket_list

def getIPs_kuaidaili():
    ips = []
    for i in range(10):
        url = 'http://www.kuaidaili.com/proxylist/%s/' % (i+1,)
        r = requests.get(url)
        soup = BeautifulSoup(r.content)
        tbody = soup.find('tbody')
        trs = tbody.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            ip = tds[0].text.strip()
            port = tds[1].text.strip()
            ips.append(ip+':'+port)
    return ips

#- -use v8 engine to eval javascript code to get port
def getIPs_org_pachong():
    #glob = Global()
    socket_list = []
    url = 'http://pachong.org/area/short/name/cn/type/high.html'
    r = requests.get(url)
    soup = BeautifulSoup(r.content)
    script = soup.findAll('script',attrs={'type':'text/javascript'})[2]
    js_code_part1 = script.text
    tbody = soup.find('tbody')
    trs = tbody.findAll('tr')
    for tr in trs:
        tds = tr.findAll('td')
        ip = tds[1].text
        js_code_part2 = tds[2].text
        with PyV8.JSIsolate():
            with PyV8.JSContext() as ctxt:
                ctxt.eval(js_code_part1)
                port = ctxt.eval(js_code_part2[15:-2])
        socket_address = '%s:%s' % (ip,port)
        proxy_type = tds[4].a.text
        if proxy_type == 'high':
            socket_list.append(socket_address)
    return socket_list

def getIPs():
    IPPool = []
    getIPs_functions = [getIPs_proxy_digger, getIPs_proxy_ru, getIPs_kuaidaili, getIPs_org_pachong]
    for getIPs_function in getIPs_functions:
        try:
            ips = getIPs_function()
            print getIPs_function.__name__,len(ips)
            IPPool.extend(ips)
        except:
            print traceback.format_exc()

    IPPool = list(set(IPPool))
    print "total IPs: " + str(len(IPPool))
    return IPPool


def verify_ip(socket_address):
    proxies = {"http":"http://" + socket_address}
    try:
        ip = socket_address.split(':')[0]
        verify_url1 = 'http://luckist.sinaapp.com/test_ip'
        verify_url2 = 'http://members.3322.org/dyndns/getip'

        r1 = requests.get(verify_url1,proxies=proxies,timeout=3)
        r2 = requests.get(verify_url2,proxies=proxies,timeout=3)
        return_ip1 = r1.content.strip()
        return_ip2 = r2.content.strip()

        if ip == return_ip1 and ip == return_ip2:
            #        if ip == return_ip1:
            return True
        else:
            return False
    except:
        return False

def worker(valid_ips,ip_list):
    for ip in ip_list:
        if verify_ip(ip) is True:
            threadLock.acquire()
            valid_ips.append(ip)
            threadLock.release()

if __name__ == "__main__":
    client = pymongo.MongoClient('58.218.248.114')
    db = client['proxy_db']
    proxy_collection = db['proxies']
    while True:
        ips = getIPs()
        valid_ips = []

        threads = []
        for i in range(ThreadNum):
            ip_list = [ip for index,ip in enumerate(ips) if index%ThreadNum==i]
            t = threading.Thread(target=worker, args=(valid_ips,ip_list))
            threads.append(t)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        print len(valid_ips)
        try:
            proxy_collection.drop()
        except Exception:
            pass
        for socket_address in valid_ips:
            ip,port = socket_address.split(':')
            print ip,port
            proxy_collection.insert({'ip':ip,'port':port})
        time.sleep(1800)
