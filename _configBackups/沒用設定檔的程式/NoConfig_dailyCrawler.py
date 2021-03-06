from datetime import datetime
import myNASsynofuncs as nas
import myNASlinefuncs as line 
import myNASkoreafuncs as korea
import myNASbeautyfuncs as beauty
import logging
import sys
import os

logging.basicConfig(filename='%s/.scheduler/.log/.dailyCrawler/%s.log' % (os.path.expanduser('~'), datetime.now().strftime('%Y%m%d_%H%M%S')), level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
# ------ 主程式 ------------------------------------------------------------------
if __name__ == '__main__':
    # --- 先啟始 LINE 通知的物件 -----------------------------       
    myLineNotificator = line.lineNotification()
    if not myLineNotificator.lineToken:
        logging.error('=== 建立 LINE Notify 時發生未預期的錯誤 ===')
        sys.exit(1)
    # --- 初始化 myKoreaCrawler 物件 -----------------------------
    myKoreaCrawler = korea.crawlerKorea()
    myLineNotificator.sendMessage('已開始[%s]作業' % myKoreaCrawler.name) 
    # --- 取得 getLoginCredential 登入網站並取得 Session -----------------------------
    myKoreaCrawler.session = myKoreaCrawler.getLoginSession()                   
    if myKoreaCrawler.session:
        myLineNotificator.sendMessage('已啟始[%s]並登入網站，開始擷取資料' % myKoreaCrawler.name)   
    else:
        myLineNotificator.sendMessage('建立[%s]的連線時發生未預期的錯誤' % myKoreaCrawler.name)        
        sys.exit(1)
    # ## === 特殊情況 === 直接讀入今天已完成的資料檔, 然後確定起始/結束序號 -----------------------------
    # if myKoreaCrawler.getJustSequencedCaster():
    #     myLineNotificator.sendMessage('[%s]已讀取今天可用的資料檔' % myKoreaCrawler.name)
    # --- 如果正常登入網站則讀入昨天的資料檔 -----------------------------
    if myKoreaCrawler.getLastSequencedCaster():
        myLineNotificator.sendMessage('[%s]已讀取昨天可用的資料檔' % myKoreaCrawler.name)
    # --- 無法讀入記錄檔 -----------------------------
    else:
        myLineNotificator.sendMessage('[%s]無法讀取最近一次可用的資料檔。' % myKoreaCrawler.name)
        sys.exit(1)
    # --- 查看有無今天的記錄檔已存在, 嘗試從當天已蒐集的記錄復原(如果有的話) -----------------------------               
    if myKoreaCrawler.recoverfromAccumulatedCasterJson():
        # --- 如果可以從當天已蒐集的記錄復原, 則起始結束序號已重設定為復原後的序號, 並延用今天的記錄檔 -----------------------------
        myLineNotificator.sendMessage('[%s]已從當天的記錄檔案復原完成。復原了[%d]筆資料。' % (myKoreaCrawler.name, len(myKoreaCrawler.accumulatedCaster)))
    else:
        # --- 查看是否有當天已蒐集的記錄並試圖讀入記錄檔回復作業 -----------------------------
        myLineNotificator.sendMessage('[%s]沒有當天的記錄檔案 (或嘗試復原記錄檔案時發生未預期的錯誤)' % myKoreaCrawler.name)
        # --- 啟始當天的記錄檔開始新的蒐集記錄 -----------------------------    
    additionalInfo = '原先已存在的蒐集記錄檔案已更改名稱，並' if myKoreaCrawler.initAccumulatedCasterJson() else ''
    myLineNotificator.sendMessage('[%s]%s已啟始當天的記錄檔 %s 開始新的蒐集記錄' % (myKoreaCrawler.name, additionalInfo, os.path.basename(myKoreaCrawler.accumulatedCasterJson)))
    # --- 如果設定開始序號有設定 ---
    if myKoreaCrawler.givenNo2Start and myKoreaCrawler.givenNo2Stop:
        myLineNotificator.sendMessage('開始[%s]擷取。起始序號[%d]。預計結束序號[%d]' % (myKoreaCrawler.name, myKoreaCrawler.givenNo2Start, myKoreaCrawler.givenNo2Stop))
    # --- 如果沒有設定開始序號(應該不會發生) -----------------------------  
    else:
        myLineNotificator.sendMessage('[%s]設定起始與結束序號時發生未預期的錯誤' % myKoreaCrawler.name)
        sys.exit(1)
    # --- 看來一切就緒我們就開始蒐集資料吧 -----------------------------
    if not myKoreaCrawler.startCrawlerProcess():
        # --- 如果抓資料中間發生錯誤 -----------------------------
        myKoreaCrawler.dumpSequencedCasterUnfihishedPickle()
        myLineNotificator.sendMessage('[%s]程式意外終止。參考中斷時的序號[%d]' % (myKoreaCrawler.name, myKoreaCrawler.casterIndexer))
        sys.exit(1)
    else:
        myLineNotificator.sendMessage('[%s]擷取順利完成。參考結束時的序號[%d]' % (myKoreaCrawler.name, myKoreaCrawler.casterIndexer))
    # --- 啟始 pttBeautyCrawler 的物件並且開始抓資料 ---   
    pttBeautyCrawler = beauty.crawlerPttBeauty()
    myLineNotificator.sendMessage('已開始[%s]作業' % pttBeautyCrawler.name)
    # ## === 特殊情況 === 直接讀入今天已完成的資料檔, 然後確定總數量 -----------------------------   
    # if pttBeautyCrawler.getJustCompletedBeautyPickle():
    #     myLineNotificator.sendMessage('[%s]已讀取今天可用的資料檔。共有[%d]篇文章，[%d]筆資料' % (pttBeautyCrawler.name, len(pttBeautyCrawler.completedBeauty['articles']), pttBeautyCrawler.itemCounter))
    # ---- 啟始記錄檔 --------------------------
    additionalInfo = '原先已存在的蒐集記錄檔案已更改名稱，並' if pttBeautyCrawler.initAccumulatedBeautyJson() else ''
    myLineNotificator.sendMessage('[%s]%s已啟始當天的記錄檔 %s 開始新的蒐集記錄' % (pttBeautyCrawler.name, additionalInfo, os.path.basename(pttBeautyCrawler.accumulatedBeautyJson)))
    # --- 看來一切就緒我們就開始蒐集資料吧 -----------------------------
    if pttBeautyCrawler.startCrawlerProcess():
        # ---- 關閉記錄檔 --------------------------        
        pttBeautyCrawler.finilizeAccumulatedBeautyJson()
        # ---- 寫入今天的資料檔 --------------------------     
        pttBeautyCrawler.dumpCompletedBeauty()
        myLineNotificator.sendMessage('已完成[%s]擷取。共有[%d]篇文章，[%d]筆資料' % (pttBeautyCrawler.name, len(pttBeautyCrawler.accumulatedArticles), pttBeautyCrawler.itemCounter))
    else:
        myLineNotificator.sendMessage('進行[%s]擷取時發生未預期的錯誤。作業未完成。參考中斷時的網址為[%s]' % (pttBeautyCrawler.name, pttBeautyCrawler.currentPage))
        sys.exit(1)
    # --- 如果抓資料順利完成, 就啟始 NAS 物件並登入 -----------------------------    
    ds214se = nas.nasDiskStation()
    # ------ 登入 NAS 失敗 -----------------------------            
    if not ds214se.login:
        myLineNotificator.sendMessage('登入 NAS [%s] 失敗' % ds214se.name)
        sys.exit(1)          
    # --- 如果登入 NAS 成功 -----------------------------    
    else:
        logging.debug('=== NAS[%s]已登入。工作階段(Session ID)為[%s] ===' % (ds214se.name, ds214se.sid))
        myLineNotificator.sendMessage('登入 NAS [%s] 成功' % ds214se.name)                        
        # ------ 開始下載 myKoreaCrawler 抓取的資料 -----------------------------
        myLineNotificator.sendMessage('進行 [%s] 下載作業，起始序號: [%d]，結束序號: [%d]' % (myKoreaCrawler.name, myKoreaCrawler.givenNo2Start, myKoreaCrawler.givenNo2Stop))
        if not myKoreaCrawler.downloadProcess(ds214se):
            myLineNotificator.sendMessage('新增 [%s] 下載作業中途意外結束。參考的索引號 [%d]' % (myKoreaCrawler.name, myKoreaCrawler.casterIndexer))
            sys.exit(1)
        else:
            myLineNotificator.sendMessage('下載作業 [%s] 已順利結束完成。起始序號: [%d]，結束序號: [%d]' % (myKoreaCrawler.name, myKoreaCrawler.givenNo2Start, myKoreaCrawler.givenNo2Stop))
        # ------ 開始下載 pttBeautyCrawler 抓取的資料 -----------------------------
        if not pttBeautyCrawler.downloadProcess(ds214se):
            myLineNotificator.sendMessage('新增 [%s] 下載作業中途意外結束。參考的索引號 [%d]' % (pttBeautyCrawler.name, pttBeautyCrawler.beautyIndexer))
            sys.exit(1)
        else:
            myLineNotificator.sendMessage('新增 [%s] 下載作業順利結束完成。參考的索引號 [%d]' % (pttBeautyCrawler.name, pttBeautyCrawler.beautyIndexer))       
    # ------ 登出 ----------------------------- 
    if not ds214se.logout():
        myLineNotificator.sendMessage('登出 NAS [%s] 失敗' % ds214se.name)
        sys.exit(1)
    else:
        myLineNotificator.sendMessage('已成功登出 NAS [%s]' % ds214se.name)