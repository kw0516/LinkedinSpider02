# encoding=utf-8
# ----------------------------------------
# 语言：Python2.7
# 日期：2017-12-04
# 功能：根据公司名称抓取员工的LinkedIn数据
# ----------------------------------------

import sys
import copy
import time
from urllib import unquote
import requests
from urllib import quote
import re
from lxml import etree

import tkMessageBox as msgbox
import tkinter as tk
import threading

reload(sys)
sys.setdefaultencoding('utf8')

CREDIT_GRADE = {  # 芝麻信用
    'EXCELLENT': '极好',
    'VERY_GOOD': '优秀',
    'GOOD': '良好',
    'ACCEPTABLE': '中等',
    'POOR': '较差'
}
LINKS_FINISHED = []  # 已抓取的linkedin用户

is_start = False


def login(laccount, lpassword):
    """ 根据账号密码登录linkedin """
    s = requests.Session()
    r = s.get('https://www.linkedin.com/uas/login')
    tree = etree.HTML(r.content)
    loginCsrfParam = ''.join(tree.xpath('//input[@id="loginCsrfParam-login"]/@value'))
    csrfToken = ''.join(tree.xpath('//input[@id="csrfToken-login"]/@value'))
    sourceAlias = ''.join(tree.xpath('//input[@id="sourceAlias-login"]/@value'))
    isJsEnabled = ''.join(tree.xpath('//input[@name="isJsEnabled"]/@value'))
    source_app = ''.join(tree.xpath('//input[@name="source_app"]/@value'))
    tryCount = ''.join(tree.xpath('//input[@id="tryCount"]/@value'))
    clickedSuggestion = ''.join(tree.xpath('//input[@id="clickedSuggestion"]/@value'))
    signin = ''.join(tree.xpath('//input[@name="signin"]/@value'))
    session_redirect = ''.join(tree.xpath('//input[@name="session_redirect"]/@value'))
    trk = ''.join(tree.xpath('//input[@name="trk"]/@value'))
    fromEmail = ''.join(tree.xpath('//input[@name="fromEmail"]/@value'))

    payload = {
        'isJsEnabled': isJsEnabled,
        'source_app': source_app,
        'tryCount': tryCount,
        'clickedSuggestion': clickedSuggestion,
        'session_key': laccount,
        'session_password': lpassword,
        'signin': signin,
        'session_redirect': session_redirect,
        'trk': trk,
        'loginCsrfParam': loginCsrfParam,
        'fromEmail': fromEmail,
        'csrfToken': csrfToken,
        'sourceAlias': sourceAlias
    }
    s.post('https://www.linkedin.com/uas/login-submit', data=payload)
    return s


def get_linkedin_url(url, s):
    global filename
    """ 百度搜索出来的是百度跳转链接，要从中提取出linkedin链接 """
    try:
        r = s.get(url, allow_redirects=False)
        if r.status_code == 302 and 'Location' in r.headers.keys() and 'linkedin.com/in/' in r.headers['Location']:
            return r.headers['Location']
    except Exception, e:
        print >> filename, u'get linkedin url failed: %s' % url
    return ''


def parse(content, url):
    global filename
    """ 解析一个员工的Linkedin主页 """
    content = unquote(content).replace('&quot;', '"')

    profile_txt = ' '.join(re.findall('(\{[^\{]*?profile\.Profile"[^\}]*?\})', content))
    firstname = re.findall('"firstName":"(.*?)"', profile_txt)
    lastname = re.findall('"lastName":"(.*?)"', profile_txt)
    if firstname and lastname:
        print >> filename, u'姓名: %s%s    Linkedin: %s' % (lastname[0], firstname[0], url)

        summary = re.findall('"summary":"(.*?)"', profile_txt)
        if summary:
            print >> filename, u'简介: %s' % summary[0]

        occupation = re.findall('"headline":"(.*?)"', profile_txt)
        if occupation:
            print >> filename, u'身份/职位: %s' % occupation[0]

        locationName = re.findall('"locationName":"(.*?)"', profile_txt)
        if locationName:
            print >> filename, u'坐标: %s' % locationName[0]

        networkInfo_txt = ' '.join(re.findall('(\{[^\{]*?profile\.ProfileNetworkInfo"[^\}]*?\})', content))
        connectionsCount = re.findall('"connectionsCount":(\d+)', networkInfo_txt)
        if connectionsCount:
            print >> filename, u'好友人数: %s' % connectionsCount[0]

        sesameCredit_txt = ' '.join(re.findall('(\{[^\{]*?profile\.SesameCreditGradeInfo"[^\}]*?\})', content))
        credit_lastModifiedAt = re.findall('"lastModifiedAt":(\d+)', sesameCredit_txt)
        credit_grade = re.findall('"grade":"(.*?)"', sesameCredit_txt)
        if credit_grade and credit_grade[0] in CREDIT_GRADE.keys():
            credit_lastModifiedAt_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(credit_lastModifiedAt[0][:10]))) if credit_lastModifiedAt else ''
            print >> filename, u'芝麻信用: %s %s' % (CREDIT_GRADE[credit_grade[0]], u'   最后更新时间: %s' % credit_lastModifiedAt_date if credit_lastModifiedAt_date else '')

        wechat_txt = ' '.join(re.findall('(\{[^\{]*?profile\.WeChatContactInfo"[^\}]*?\})', content))
        wechat_image = re.findall('"qrCodeImageUrl":"(http.*?)"', wechat_txt)
        wechat_name = re.findall('"name":"(.*?)"', wechat_txt)
        if wechat_name:
            print >> filename, u'微信昵称: %s %s' % (wechat_name[0], u'    二维码(链接): %s' % wechat_image[0].replace('&#61;', '=').replace('&amp;', '&') if wechat_image else '')
        elif wechat_image:
            print >> filename, u'微信二维码(链接): %s' % wechat_image[0].replace('&#61;', '')

        website_txt = ' '.join(re.findall('("included":.*?profile\.StandardWebsite",.*?\})', content))
        website = re.findall('"url":"(.*?)"', website_txt)
        if website:
            print >> filename, u'个人网站: %s' % website[0]

        educations = re.findall('(\{[^\{]*?profile\.Education"[^\}]*?\})', content)
        if educations:
            print >> filename, u'教育经历:'
        for one in educations:
            schoolName = re.findall('"schoolName":"(.*?)"', one)
            fieldOfStudy = re.findall('"fieldOfStudy":"(.*?)"', one)
            degreeName = re.findall('"degreeName":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            schoolTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                schoolTime += '   %s ~ %s' % (startdate, enddate)
            if schoolName:
                fieldOfStudy = '   %s' % fieldOfStudy[0] if fieldOfStudy else ''
                degreeName = '   %s' % degreeName[0] if degreeName else ''
                print >> filename, u'    %s %s %s %s' % (schoolName[0], schoolTime, fieldOfStudy, degreeName)

        position = re.findall('(\{[^\{]*?profile\.Position"[^\}]*?\})', content)
        if position:
            print >> filename, u'工作经历:'
        for one in position:
            companyName = re.findall('"companyName":"(.*?)"', one)
            title = re.findall('"title":"(.*?)"', one)
            locationName = re.findall('"locationName":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            positionTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                positionTime += '   %s ~ %s' % (startdate, enddate)
            if companyName:
                title = '   %s' % title[0] if title else ''
                locationName = '   %s' % locationName[0] if locationName else ''
                print >> filename, u'    %s %s %s %s' % (companyName[0], positionTime, title, locationName)

        publication = re.findall('(\{[^\{]*?profile\.Publication"[^\}]*?\})', content)
        if publication:
            print >> filename, u'出版作品:'
        for one in publication:
            name = re.findall('"name":"(.*?)"', one)
            publisher = re.findall('"publisher":"(.*?)"', one)
            if name:
                print >> filename, u'    %s %s' % (name[0], u'   出版社: %s' % publisher[0] if publisher else '')

        honor = re.findall('(\{[^\{]*?profile\.Honor"[^\}]*?\})', content)
        if honor:
            print >> filename, u'荣誉奖项:'
        for one in honor:
            title = re.findall('"title":"(.*?)"', one)
            issuer = re.findall('"issuer":"(.*?)"', one)
            issueDate = re.findall('"issueDate":"(.*?)"', one)
            issueTime = ''
            if issueDate:
                issueDate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s"[^\}]*?\})' % issueDate[0].replace('(', '\(').replace(')', '\)'), content))
                year = re.findall('"year":(\d+)', issueDate_txt)
                month = re.findall('"month":(\d+)', issueDate_txt)
                if year:
                    issueTime += '   发行时间: %s' % year[0]
                    if month:
                        issueTime += '.%s' % month[0]
            if title:
                print >> filename, u'    %s %s %s' % (title[0], u'   发行人: %s' % issuer[0] if issuer else '', issueTime)

        organization = re.findall('(\{[^\{]*?profile\.Organization"[^\}]*?\})', content)
        if organization:
            print >> filename, u'参与组织:'
        for one in organization:
            name = re.findall('"name":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            organizationTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                organizationTime += '   %s ~ %s' % (startdate, enddate)
            if name:
                print >> filename, u'    %s %s' % (name[0], organizationTime)

        patent = re.findall('(\{[^\{]*?profile\.Patent"[^\}]*?\})', content)
        if patent:
            print >> filename, u'专利发明:'
        for one in patent:
            title = re.findall('"title":"(.*?)"', one)
            issuer = re.findall('"issuer":"(.*?)"', one)
            url = re.findall('"url":"(http.*?)"', one)
            number = re.findall('"number":"(.*?)"', one)
            localizedIssuerCountryName = re.findall('"localizedIssuerCountryName":"(.*?)"', one)
            issueDate = re.findall('"issueDate":"(.*?)"', one)
            patentTime = ''
            if issueDate:
                issueDate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s"[^\}]*?\})' % issueDate[0].replace('(', '\(').replace(')', '\)'), content))
                year = re.findall('"year":(\d+)', issueDate_txt)
                month = re.findall('"month":(\d+)', issueDate_txt)
                day = re.findall('"day":(\d+)', issueDate_txt)
                if year:
                    patentTime += '   发行时间: %s' % year[0]
                    if month:
                        patentTime += '.%s' % month[0]
                        if day:
                            patentTime += '.%s' % day[0]
            if title:
                print >> filename, u'    %s %s %s %s %s %s' % (title[0], u'   发行者: %s' % issuer[0] if issuer else '', u'   专利号: %s' % number[0] if number else '', u'   所在国家: %s' % localizedIssuerCountryName[0] if localizedIssuerCountryName else '', patentTime, u'   专利详情页: %s' % url[0] if url else '')

        project = re.findall('(\{[^\{]*?profile\.Project"[^\}]*?\})', content)
        if project:
            print >> filename, u'所做项目:'
        for one in project:
            title = re.findall('"title":"(.*?)"', one)
            description = re.findall('"description":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            projectTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                projectTime += '   时间: %s ~ %s' % (startdate, enddate)
            if title:
                print >> filename, u'    %s %s %s' % (title[0], projectTime, u'   项目描述: %s' % description[0] if description else '')

        volunteer = re.findall('(\{[^\{]*?profile\.VolunteerExperience"[^\}]*?\})', content)
        if volunteer:
            print >> filename, u'志愿者经历:'
        for one in volunteer:
            companyName = re.findall('"companyName":"(.*?)"', one)
            role = re.findall('"role":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            volunteerTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                volunteerTime += '   时间: %s ~ %s' % (startdate, enddate)
            if companyName:
                print >> filename, u'    %s %s %s' % (companyName[0], volunteerTime, u'   角色: %s' % role[0] if role else '')
    print >> filename, u'\n\n'


def crawl(url, s):
    """ 抓取每一个搜索结果 """
    global filename
    try:
        url = get_linkedin_url(url, copy.deepcopy(s)).replace('cn.linkedin.com', 'www.linkedin.com')  # 百度搜索出的结果是百度跳转链接，要提取出linkedin的链接。
        if len(url) > 0 and url not in LINKS_FINISHED:
            LINKS_FINISHED.append(url)

            failure = 0
            while failure < 10:
                try:
                    r = s.get(url, timeout=10)
                except Exception, e:
                    failure += 1
                    continue
                if r.status_code == 200:
                    parse(r.content, url)
                    break
                else:
                    print >> filename, u'%s %s' % (r.status_code, url)
                    failure += 2
            if failure >= 10:
                print >> filename, u'Failed: %s' % url
    except Exception, e:
        pass


def runSpider(username = '', password = '', company =''):
    global filename,is_start
    if is_start:
        return
    is_start = True
    filename = open(company + ".txt", "w")
    s = login(laccount=username, lpassword=password)  # 测试账号
    company_name = company

    maxpage = 30  # 抓取前50页百度搜索结果，百度搜索最多显示76页
    if app.v.get() == 2:
        maxpage = 50
    tempPage = maxpage

    # 百度搜索
    url = 'http://www.baidu.com/s?ie=UTF-8&wd=%20%7C%20领英%20' + quote(company_name) + '%20site%3Alinkedin.com'
    results = []
    failure = 0
    while len(url) > 0 and failure < 10:
        try:
            r = requests.get(url, timeout=10)
        except Exception, e:
            failure += 1
            continue
        if r.status_code == 200:
            hrefs = list(set(re.findall('"(http://www\.baidu\.com/link\?url=.*?)"', r.content)))  # 一页有10个搜索结果
            for href in hrefs:
                crawl(href, copy.deepcopy(s))
            results += hrefs
            tree = etree.HTML(r.content)
            nextpage_txt = tree.xpath('//div[@id="page"]/a[@class="n" and contains(text(), "下一页")]/@href'.decode('utf8'))
            url = 'http://www.baidu.com' + nextpage_txt[0].strip() if nextpage_txt else ''
            failure = 0
            maxpage -= 1
            if maxpage <= 0:
                app.proccess.set(u"下载数据完成！保存在文件%s.txt下"%company)
                break
            app.proccess.set(u"抓取数据中...%.0f%%"%(100*(tempPage-maxpage)/tempPage))
        else:
            failure += 2
            print >> filename, u'search failed: %s' % r.status_code
    if failure >= 10:
        print >> filename, u'search failed: %s' % url
        app.proccess.set(u"下载数据失败！")
    is_start = False
    filename.close()

class DownloadData(threading.Thread):
    def __init__(self, u, p, c):
        threading.Thread.__init__(self)
        self.username = u
        self.password = p
        self.company = c

    def run(self):
        runSpider(username= self.username, password = self.password, company=self.company)


class APP:
    def __init__(self, width=500, height=350):
        self.w = width
        self.h = height
        self.title = ' LinkedIn数据爬取'
        self.root = tk.Tk(className=self.title)
        self.url = tk.StringVar()
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.proccess = tk.StringVar()
        self.v = tk.IntVar()
        self.v.set(1)

        # Frame空间
        frame_1 = tk.Frame(self.root)
        frame_2 = tk.Frame(self.root)
        frame_3 = tk.Frame(self.root)

        # Menu菜单
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        filemenu = tk.Menu(menu, tearoff=0)
        moviemenu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label='菜单', menu=filemenu)
        filemenu.add_command(label='使用说明', command=lambda: msgbox.showinfo(title='使用说明', message='根据公司名抓取员工Linkedin数据'))
        filemenu.add_command(label='关于作者', command=lambda: msgbox.showinfo(title='关于作者', message='田园黑叔叔'))
        filemenu.add_command(label='退出', command=self.root.quit)


        # 控件内容设置
        group0 = tk.Label(frame_1, text='请选择一个下载模式：', padx=10, pady=10)
        tb1 = tk.Radiobutton(frame_1, text='普通模式', variable=self.v, value=1, width=10, height=3)
        tb2 = tk.Radiobutton(frame_1, text='强力模式', variable=self.v, value=2, width=10, height=3)
        group = tk.Label(frame_1, text='请输入用户名：', padx=10, pady=10)
        un = tk.Entry(frame_1, textvariable=self.username, highlightcolor='Fuchsia', highlightthickness=1, width=30)
        group2 = tk.Label(frame_1, text='请输入密码：', padx=10, pady=10)
        pw = tk.Entry(frame_1, textvariable=self.password, highlightcolor='Fuchsia', highlightthickness=1, width=30,show='*')
        label1 = tk.Label(frame_2, text="请输入公司名称：")
        entry = tk.Entry(frame_2, textvariable=self.url, highlightcolor='Fuchsia', highlightthickness=1, width=35)
        label2 = tk.Label(frame_2, text=" ")
        play = tk.Button(frame_2, text="开始", font=('楷体', 12), fg='Purple', width=2, height=1, command=self.start)
        label3 = tk.Label(frame_2, text=" ")
        label_proccess = tk.Label(frame_3, textvariable=self.proccess, fg='blue', font=('楷体', 12), text='')
        label_explain = tk.Label(frame_3, fg='red', font=('楷体', 12),
                                 text='\n注意：请在浏览器中登录您输入的领英帐号再使用本软件！\n此软件会抓取可能的匹配数据，最终数据的可用性还需要您的甄别！\n此软件仅用于交流学习，请勿用于任何商业用途！')
        label_warning = tk.Label(frame_3, fg='blue', font=('楷体', 12), text='\n建议：普通模式下若没有您需要的数据，请尝试强力模式！')

        # 控件布局
        frame_1.pack()
        frame_2.pack()
        frame_3.pack()
        group0.grid(row=0, column=0)
        tb1.grid(row=0, column=1)
        tb2.grid(row=0, column=2)
        group.grid(row=1, column=0)
        un.grid(row=1, column=1)
        group2.grid(row=2, column=0)
        pw.grid(row=2, column=1)
        label1.grid(row=0, column=0)
        entry.grid(row=0, column=1)
        label2.grid(row=0, column=2)
        play.grid(row=0, column=3, ipadx=10, ipady=10)
        label3.grid(row=0, column=4)
        label_proccess.grid(row=0, column=0)
        label_explain.grid(row=1, column=0)
        label_warning.grid(row=2, column=0)

    """
    函数说明:视频播放

    Parameters:
    	self

    Returns:
    	无

    Modify:
    	2017-05-09
    """

    def start(self):
        #
        if self.username.get() == '':
            msgbox.showerror(title='错误', message='请输入用户名！')
        elif self.password.get() == '':
            msgbox.showerror(title='错误', message='请输入密码！')
        elif self.url.get() == '':
            msgbox.showerror(title='错误', message='请输入公司名称！')
        else:
            app.proccess.set(u"准备抓取数据，请稍候...")
            my_data = DownloadData(self.username.get(),self.password.get(),self.url.get())
            my_data.start()

    """
    函数说明:tkinter窗口居中

    Parameters:
    	self

    Returns:
    	无

    Modify:
    	2017-05-09
    """

    def center(self):
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = int((ws / 2) - (self.w / 2))
        y = int((hs / 2) - (self.h / 2))
        self.root.geometry('{}x{}+{}+{}'.format(self.w, self.h, x, y))

    """
    函数说明:loop等待用户事件

    Parameters:
    	self

    Returns:
    	无

    Modify:
    	2017-05-09
    """

    def loop(self):
        self.root.resizable(False, False)  # 禁止修改窗口大小
        self.center()  # 窗口居中
        self.root.mainloop()

if __name__ == '__main__':
    app = APP()  # 实例化APP对象
    app.loop()  # loop等待用户事件
