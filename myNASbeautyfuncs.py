# --- The MIT License (MIT) Copyright (c) alvinconstantine(alvin.constantine@outlook.com), Sat Jun 21 09:58am 2020 ---
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Tag
from time import strftime, sleep
import os, sys, shutil
import logging
import requests
import pickle
import json
import re

# --- 定義 pttBeauty crawler 類別 -------------------------- 
class crawlerPttBeauty():
    def __init__(self):
        # --- 常變數設定 --------------------------
        self.name = 'pttbeauty'
        self.userbaseDir = os.path.expanduser('~') 
        self.storageData = '%s/%s/%s' % ('.scheduler', self.name, 'crawlerdata')
        self.storageDownload = '%s/%s/%s' % ('.scheduler', self.name, 'downloads')
        self.timeFreeze = datetime.now()
        self.timeYesterday = (self.timeFreeze - timedelta(days=1)).strftime('%m/%d').lstrip('0')
        self.formatYesterday = (self.timeFreeze - timedelta(days=1)).strftime('%Y%m%d')
        self.accumulatedBeautyJson = '%s/%s/sequencedBeautyJson_%s.json' % (self.userbaseDir, self.storageData, self.formatYesterday)
        self.completedBeautyPickle = '%s/%s/completedBeautyPickle_%s.pickle' % (self.userbaseDir, self.storageData, self.formatYesterday)
        self.completedBeautyJson = '%s/%s/completedBeautyJson_%s.json' % (self.userbaseDir, self.storageData, self.formatYesterday)
        self.isoformatYesterday = (self.timeFreeze - timedelta(days=1)).strftime('%Y-%m-%d')
        self.intYesterday = int(self.timeYesterday.replace('/', ''))
        self.appScheme = 'https://www.ptt.cc'
        self.currentPage = '%s%s' % (self.appScheme, '/bbs/Beauty/index.html')        
        self.accumulatedArticles = []  # 儲存取得的文章資料
        self.incompletedArticles = []  # 儲存未完的文章資料
        self.completedBeauty = {}
        self.pageCounter = 0
        self.itemCounter = 0
        self.validArticles = 0
        self.beautyIndexer = 0
        self.session = None
        self.cookies = {
            'over18': '1'
            }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0',
            }
        self.knownFileExtensions = ('jpg', 'png', 'gif', 'mp4', 'jpeg')

    # --- 開始擷取頁面 -------------------------- 
    def startCrawlerProcess(self):
        # --- 篩選標題函式 --------------------------
        def contentShrink(content):
            try:
                content = re.sub('(Sent from (.)+\.)|(/cdn-cgi/l/email-protection)|(=///=)|(m\(_ _\)m)|(=\s)+', '', content) # 文章本文移除無意義的內容
                content = re.sub('(\\+)|(<︰)|(づ′・ω・ づ)|(T_T)|(=\.=)|(==+)|(QAQ)|(Orz)|(orz)|(xd+)|(QQ)|(qq)|(XD+)|(0\.0)|(\^_\^.?)|(-+)|(:\))|(：）)|(\.\n)|(\.\.+)|[▲○★☆●√＊✈☛→☑□■◆✓◎‧﹨／「」【】『』《》╰╮ ╯◥◣◢◤◣︽▃▉█║▌▍═≡…囧（）＞。,，、％%；～~‼！!？｜|\^+\?\*]\s?', ' ', content) # 文章本文移除多餘的內容
                content = re.sub('[\s]+', ' ', content) # 文章本文移除多餘的空白
                content = content.lstrip().rstrip() # 文章本文移除多餘的空白
                content = content.replace('：', ':') # 替換為半形的冒號
                content = content.replace('{_', '{') # 替換{_為{號
                content = content.replace('//', '') # 移除//
                content = content.replace('#', '') # 移除 #
                content = content.replace(' ', '') # 移除 空白
            except Exception as e:
                logging.error('=== 在縮減內容時發生意外錯誤: [%s] ===' % str(e))
            finally:
                return content
        # --- 要求網頁頁面函式 --------------------------          
        def getwebPage(url):            
            if self.session == None:
                with requests.Session() as session:  
                   responsedPage = session.get(url, headers=self.headers, cookies=self.cookies)
            else:
                responsedPage = self.session.get(url, headers=self.headers, cookies=self.cookies)
            if responsedPage.status_code != 200:
                logging.error('=== 取得頁面網址 [%s] 失敗! ===' % url)            
                self.session = None
                return None
            else:       
                logging.debug('=== 取得頁面網址 [%s] 成功! ===' % url)
                if self.session == None:
                    self.session = session
                return responsedPage.text
        # --- 分析網頁頁面函式 --------------------------
        def parseResponsedPage(respPage):
            respSoup = BeautifulSoup(respPage, 'html5lib')
            # --- 把擷取到的上一頁的連結最後回傳給主程式並且頁數加1 --------------------------                
            naviPaging = respSoup.find('div', 'btn-group btn-group-paging')
            nextPage = None            
            try:
                pageHref  = naviPaging.find_all('a')[1]['href']
            except Exception:
                logging.error('=== 在分析頁面網址 %s 中導覽列的上下頁連結時發生未預期的錯誤: [%s] ===' % (self.currentPage, str(e)))
            else:
                nextPage = '%s%s' % (self.appScheme, pageHref)  
            self.pageCounter +=1
            # --- 取得頁面所有的文章 --------------------------
            articles = None
            try:                                                        
                articles = respSoup.find_all('div', 'r-ent')
            except Exception:
                logging.error('=== 在分析頁面網址 %s 中的文章清單時發生未預期的錯誤: [%s] ===' % (self.currentPage, str(e)))
            else:
                beautyMatadata = None
                if articles:
                    for article in articles:
                        artdate, pageurl, title, author = '', '', '', ''
                        artdate = article.find('div', 'date').text.strip()
                        # --- 確認發文日期並且該文章存在未被刪除 --------------------------                                  
                        logging.debug('=== 抓到的文章日期: [%s] ===' % artdate)
                        logging.debug('=== 預期的文章日期: [%s] ===' % self.timeYesterday)                                     
                        if artdate == self.timeYesterday and article.find('a'):
                            # --- 取得文章連結及標題, 超連結 --------------------------                                     
                            pageurl = article.find('a')['href']
                            logging.debug('=== 取得的 pageurl: [%s] ===' % pageurl)
                            title = contentShrink(article.find('a').text)
                            logging.debug('=== 取得的 title: [%s] ===' % title)
                            author = article.find('div', 'author').text if article.find('div', 'author') else ''
                            logging.debug('=== 取得的 author: [%s] ===' % author)
                            # --- 篩選文章 --------------------------
                            if not '[公告]' in title and not '[Beauty] 看板 選情報導' in title:
                                # --- 取得文章內文 --------------------------
                                pageurl = '%s%s' % (self.appScheme, pageurl)                                                       
                                respBtyPage = getwebPage(pageurl)
                                if respBtyPage:
                                    self.validArticles += 1
                                    logging.info('=== 第[%d]篇_%s |網址_[%s] ===' % (self.validArticles, title, pageurl))                          
                                    respBtySoup = BeautifulSoup(respBtyPage, 'html.parser')
                                    links = respBtySoup.find('div', id='main-content').children
                                    # --- 用擷取的資料來建立文章的 metadata --------------------------
                                    beautyMatadata = {
                                        'pageurl' : pageurl,
                                        'title' : title,
                                        'author' : author,
                                        }
                                    # --- 尋找並擷取文章的 img_url/href_urls --------------------------                                
                                    img_urls = []
                                    href_urls = [] 
                                    try:
                                        for link in links:
                                            if isinstance(link, Tag):
                                                if link.name == 'div' and 'push' in link['class']:
                                                    break
                                                elif link.name == 'a':               
                                                    link_url = link['href']
                                                    # --- link_copnts 是將網頁拆成不同組件 以便先做網頁連結的分析再做處理 --------------------------
                                                    link_copnts = link_url.split('/')
                                                    # --- 開頭是 // 而且沒有 http 或 https
                                                    if len(link_copnts) > 3:
                                                        if 'http' not in link_copnts[0] and not link_copnts[0] and not link_copnts[1]:     
                                                            link_url = 'https:' + link_url
                                                        # --- 開頭是 /bbs/ 而且沒有 http 或 https --------------------------                
                                                        elif link_copnts[1] == 'bbs':     
                                                            link_url = 'https://www.ptt.cc' + link_url
                                                            link_copnts = link_url.split('/')
                                                        # --- 如果是由 'imgur' 網域來的連結則 link_url 需特別處理將 link_url 擷取僅為圖片或影片的連結 --------------------------
                                                        elif 'imgur' in link_copnts[2]:     
                                                            if link_copnts[2].startswith('m.'):
                                                                link_url = link_url.replace('//m.', '//i.')
                                                            if not link_copnts[2].startswith('i.'):
                                                                link_url = link_url.replace(link_copnts[2], 'i.'+link_copnts[2])
                                                            if not '.' in link_copnts[-1]:
                                                                link_url = link_url + '.jpg'
                                                            elif link_url.endswith('.'):
                                                                link_url = link_url + 'jpg'
                                                        # --- 至此綱頁結構應已正確, 接著處理網頁檔名的附檔名 linkURLextension 為擷取的附檔名 --------------------------
                                                        linkURLextension = link_url.split('.')[-1]       
                                                        # --- 附檔名是已知的圖片或影片 - 加進 img_urls
                                                        if linkURLextension.lower() in self.knownFileExtensions:
                                                            img_urls.append(link_url)                                                                            
                                                        elif len(linkURLextension) > 3 and linkURLextension.lower()[:3] in self.knownFileExtensions:
                                                            img_urls.append(link_url.replace(linkURLextension, linkURLextension[:3]))                                                    
                                                        # --- 其他附檔名包含像 '.html' 的網頁連結 - 加進 href_urls --------------------------
                                                        else: 
                                                            href_urls.append(link_url)
                                                    else:
                                                        logging.info('=== 此頁面網址 [%s] 中的 [%s] 文章裡有非正確的網址 [%s] ===' % (pageurl, title, link_url))
                                        # --- 如果這篇文章有擷取到 img_urls 或/和 href_urls 則將資料加入文章的 metadata --------------------------
                                        if img_urls:
                                            self.itemCounter += len(img_urls)
                                            beautyMatadata['img_urls'] = img_urls
                                        if href_urls:
                                            beautyMatadata['href_urls'] = href_urls
                                        # --- 最後將這篇文章加入累加的文章清單然後寫入暫存檔案 --------------------------
                                        self.accumulatedArticles.append(beautyMatadata)
                                        with open(self.accumulatedBeautyJson, 'a', encoding='utf-8') as f:
                                            json.dump(beautyMatadata, f, ensure_ascii=False, indent=2)
                                            f.write(',')
                                    except Exception as e:
                                        logging.error('=== 在讀取頁面網址 [%s] 的文章 [%s] 時發生未知的錯誤: [%s] ===' % (pageurl, title, str(e)))
                                        continue
                        # --- 如果發文日期非預期日期或文章已被刪除 --------------------------
                        else:                        
                            if int(artdate.replace('/', '')) < self.intYesterday:
                                self.invalidArticles += 1
                            logging.debug('=== 此頁面中沒有預期要找的文章。累積的編號: [%d] ===' % self.invalidArticles)
                else:
                    logging.warning('=== 此頁面網址中沒有文章清單: %s ===' % self.currentPage)
                if not beautyMatadata:
                    logging.info('=== 此頁面網址中的文章清單內沒有預期日期的文章: %s ===' % self.currentPage)
            # --- 這頁文章已擷取完畢。如果有正確抓到下頁連結則回傳該連結 --------------------------
            if nextPage:
                return nextPage
            else:
                return False
        # --- 函數 startCrawlerProcess 的主程式 --------------------------
        while self.pageCounter < 10:            
            logging.info('===[ 進行中的頁面 | 第 %d 頁 | 網址 %s ]===' % (self.pageCounter, self.currentPage))
            self.invalidArticles = 0
            nextPage = None            
            respPage = getwebPage(self.currentPage)            
            if respPage:
                nextPage = parseResponsedPage(respPage)
            else:                
                self.incompletedArticles.append(self.currentPage)
            # --- 如果每頁 20 篇文章中有超過 19 篇的日期都不是預期的日期 --------------------------
            if self.invalidArticles > 19:  
                if self.incompletedArticles:                 
                    logging.info('=== 尚有 [%d] 篇文章在採集中發生連線錯誤。嘗試繼續完成並放慢速度 ===' % len(self.incompletedArticles))
                    sleepLonger = 10
                    while self.incompletedArticles:
                        self.currentPage = self.incompletedArticles.pop()
                        logging.info('===[ 終場加映頁 | 剩 %d 篇 | 網址 %s ]===' % (len(self.incompletedArticles), self.currentPage))
                        respPage = getwebPage(self.currentPage)            
                        if respPage:
                            parseResponsedPage(respPage)
                        else:
                            logging.info('=== 嘗試[%s]仍失敗再試一次 ===' % self.currentPage)
                            self.incompletedArticles.append(self.currentPage)
                            sleep(sleepLonger)
                            sleepLonger += 2
                        if sleepLonger > 20:
                            logging.error('=== 網站似乎有問題。已嘗試超過 %d 秒。尚有 %d 篇未完成' % (sleepLonger, len(self.incompletedArticles)))
                            break
                logging.info('===[ 已完成 %s 日的文章抓取。頁面網址 %s 中已沒有當天資料 ]===' % (self.timeYesterday, self.currentPage))
                break
            else:
                if nextPage:
                    self.currentPage = nextPage
                else:
                    logging.error('=== 網站似乎有問題。在頁面網址 %s 中沒有下一頁的連結資訊 ===' % self.currentPage)
                    return False
        return True

    # --- 啟始今天的 accumulatedBeautyJson 檔案 --------------------------               
    def initAccumulatedBeautyJson(self):
        existingFile = False        
        nameIndex = 0
        accumulatedBeautyJson = self.accumulatedBeautyJson
        if os.path.exists(accumulatedBeautyJson) and os.path.isfile(accumulatedBeautyJson):
            while os.path.exists(accumulatedBeautyJson) and os.path.isfile(accumulatedBeautyJson):
                nameIndex += 1
                accumulatedBeautyJson = '%s_%d.json' % (self.accumulatedBeautyJson.rstrip('.json'), nameIndex)
            try:
                shutil.move(self.accumulatedBeautyJson, accumulatedBeautyJson)
            except Exception as e:
                logging.error('=== 在更改資料檔 %s 為 %s 時錯誤, 失敗原因: %s ===' % (self.accumulatedBeautyJson, accumulatedBeautyJson, str(e)))
            else:
                logging.info('=== 已將已存在的[%s]檔案，更改名稱為[%s] ===' % (self.accumulatedBeautyJson, accumulatedBeautyJson))               
                existingFile = True               
        try:
            with open(self.accumulatedBeautyJson, 'w', encoding='utf-8') as f:
                f.write('[')
        except Exception as e:
            logging.error('=== 儲存當天資料檔 %s 錯誤, 失敗原因: %s ===' % (self.accumulatedBeautyJson, str(e)))
        else:            
            return existingFile

    # --- 結束當天的 json 的檔案並修正檔案尾端的逗號為方括號 --------------------------            
    def finalizeAccumulatedBeautyJson(self):
        try:
            with open(self.accumulatedBeautyJson, 'r+b') as f:
                f.seek(-2, os.SEEK_END)
                removeComma = f.read()
                if removeComma == b'},':
                    repsquareBracket = removeComma.replace(b'},', b'}]')
                    f.seek(-2, os.SEEK_END)
                    f.write(repsquareBracket)
        except Exception as e:
            logging.error('=== 儲存當天資料檔 %s 錯誤, 失敗原因: %s ===' % (self.accumulatedBeautyJson, str(e)))

    # --- 把當天的結果寫入 pickle/json  的 dump 檔案 --------------------------                 
    def dumpCompletedBeauty(self):
        self.completedBeauty = { 
            'date': self.isoformatYesterday,
            'items' : self.itemCounter, 
            'articles' : self.accumulatedArticles 
            }
        try:
            with open(self.completedBeautyPickle, 'wb') as f:
                pickle.dump(self.completedBeauty, f)
        except Exception as e:
            logging.error('=== 儲存當天資料檔 %s 錯誤, 失敗原因: %s ===' % (self.completedBeautyPickle, str(e)))
        try:
            with open(self.completedBeautyJson, 'w', encoding='utf-8') as f:
                json.dump(self.completedBeauty, f, ensure_ascii=False, indent=2) 
        except Exception as e:
            logging.error('=== 儲存當天資料檔 %s 錯誤, 失敗原因: %s ===' % (self.completedBeautyJson, str(e)))

    # --- 試圖讀取當天的 Pickle 結果資料檔 --------------------------    
    def getJustCompletedBeautyPickle(self):
        try:
            with open(self.completedBeautyPickle, 'rb') as f:
                self.completedBeauty = pickle.load(f)
        except Exception as e:
            logging.error('=== 讀取當天資料檔錯誤, 失敗原因: %s ===' % str(e))
            return None
        if self.completedBeauty:
            self.itemCounter = self.completedBeauty['items']
            return True

    # --- 試圖讀取當天的 Json 結果資料檔 --------------------------    
    def getJustAccumulatedJson(self):
        try:
            with open(self.accumulatedBeautyJson, 'r', encoding='utf-8') as f:
                self.accumulatedArticles = json.load(f)
        except Exception as e:
            logging.error('=== 讀取當天資料檔錯誤, 失敗原因: %s ===' % str(e))
            return None
        if self.accumulatedArticles:
            return True

    # --- 開始執行下載作業 --------------------------                         
    def downloadProcess(self, diskStation, **kwargs):
        # --- 試圖解讀日期資料 --------------------------
        def getDateFromFilename(filename):                    
            try:
                getDate = filename[filename.find('_')+1:filename.rfind('.')]
            except Exception as e:
                logging.error('=== 讀取日期資料錯誤, 失敗原因: %s ===' % str(e))
                return None
            return getDate
        # --- 試圖修正標題資料 --------------------------    
        def getTitleRight(title):
            acceptedAlnum = ('[', ']')
            isalnumConjunction = []
            appendix = ''
            try:
                if not title:
                    title = '[空白]此篇文章沒有標題'
                    logging.warning('=== 使用 [%s] 作為文章標題名稱 ===' % title)
                if ':' in title:
                    colonCount = title.count(':')
                    colonIndex = title.find(':')
                    lBracket = title.find('[')
                    rBracket = title.find(']')
                    if colonIndex<lBracket<rBracket:
                        strb4colon = title[:title.find(':')+1]
                        title = title.replace(strb4colon, '')
                        appendix = '以及文章標題中的 [%s] ' % strb4colon
                    title = title.replace(':', '')
                    logging.warning("=== 文章中的 %d 個冒號%s已被移除。目前以 '%s' 作為文章標題名稱 ===" % (colonCount, appendix, title))           
                for i in title:
                    if not i.isalnum() and i not in acceptedAlnum:
                        isalnumConjunction.append(i)
                if isalnumConjunction:
                    for j in isalnumConjunction:
                        title.replace(j, '')                    
            except Exception as e:
                logging.error('=== 嘗試修正 %s 錯誤, 失敗原因: %s ===' % (title, str(e)))
            finally:
                return title          
        # --- 確定日期為資料夾名稱 --------------------------    
        getDate = None
        if kwargs:
            if 'filename' in kwargs.keys():
                logging.info('=== 使用資料檔作為下載，檔名[%s] ===' % kwargs['filename'])
                getDate = getDateFromFilename(kwargs['filename'])
        elif self.completedBeauty:
            getDate = self.completedBeauty['date'].replace('-', '')
            self.accumulatedArticles = self.completedBeauty['articles']
            logging.info('=== 使用 %s 取得日期為[%s] ===' % (self.completedBeautyPickle, getDate))
        if not getDate:
            getDate = self.formatYesterday
            logging.debug('=== 使用 %s 取得日期為[%s] ===' % (self.formatYesterday, getDate))
        # --- 開始執行主要程式 --------------------------
        logging.info('=========[ 使用日期 %s 作為資料夾名稱 ]=========' % getDate)
        for self.beautyIndexer, task in enumerate(self.accumulatedArticles):
            title = getTitleRight(task['title'])
            if 'img_urls' in task:
                # --- 文章上層主資料夾 --------------------------
                folderExists = None 
                folder = '%s/%s' % (getDate, title)               
                ds_folder = '%s/%s' % (self.storageDownload, folder)               
                logging.debug('=== 資料夾名稱為 [%s] ===' % ds_folder)         
                if os.path.isdir('%s/%s' % (self.userbaseDir, ds_folder)):  # --- 資料夾已存在
                    logging.debug('=== 資料夾 [%s] 已存在 ===' % ds_folder)
                    diskStation.folder = ds_folder
                    folderExists = True  
                else:  # --- 資料夾不存在
                    if '肉特' in title:
                        logging.info('=== 跳過資料夾 [%s] ===' % ds_folder)
                        continue
                    else:
                        folderExists = False
                # --- 進行表特影像檔下載 -----------------------------
                logging.info('===[ 第 %d 篇|共有 %d 項|準備下載到資料夾 %s/%s ]===' % (self.beautyIndexer+1, len(task['img_urls']), self.userbaseDir, ds_folder))
                img_urls = []
                for index, img in enumerate(task['img_urls']):
                    imgFile = os.path.basename(img)                    
                    if os.path.isfile('%s/%s/%s' % (self.userbaseDir, ds_folder, imgFile)):  # ---檔案已存在                        
                        logging.info('=== %2d.檔案 [%s] 已存在。將排除 [%s] ===' % (index+1, imgFile, img))
                    else:
                        logging.info('=== %2d.檔案 [%s] 未下載。將新增 [%s] ===' % (index+1, imgFile, img))
                        img_urls.append(img)
                if img_urls:
                    if not folderExists:
                        logging.debug('=== 試圖建立資料夾 [%s] ===' % ds_folder)
                        if diskStation.FileStation('create', folder=ds_folder):
                            logging.debug('=== 建立資料夾 [%s] 成功 ===' % ds_folder)
                            folderExists = True 
                        else:
                            logging.error('=== 建立資料夾 [%s] 失敗 ===' % ds_folder)
                            return False
                    if folderExists:             
                        if diskStation.DownloadStation('create', data=img_urls):
                            logging.info('=========[ 成功|文章 %s |已新增 %d 項影像表列到下載清單 ]=========' % (title, len(img_urls)))
                        else:
                            logging.error('=========[ 失敗|文章 %s |未新增 %d 項影像表列到下載清單 ]=========' % (title, len(img_urls)))
                            return False
                    else:
                        logging.error('=== 因無法新增資料夾 %s，因此文章 %s 中 %d 項影像表列未新增到下載清單 ]=========' % (ds_folder, title, len(img_urls)))
                else:
                    logging.info('=========[ 此篇文章沒有下載任務 ]=========')
            else:
                logging.info('===[ 第 %d 篇|沒有項目|此篇文章 [%s] 沒有圖片 ===' % (self.beautyIndexer+1, title))
            if 'href_urls' in task:
                for index, href in enumerate(task['href_urls']):
                    logging.info('========= %2d.參考的連結 [%s]。此連結不會新增下載 =========' % (index+1, href))                    
        return True