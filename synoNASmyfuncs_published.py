# --- The MIT License (MIT) Copyright (c) alvinlin, Fri May 2nd 02:35:00 2020 ---
from requests.compat import urljoin
from pymongo import MongoClient
from pymongo import DESCENDING
from datetime import datetime
import requests
import logging
import json
import os, sys

logging.basicConfig(level = logging.INFO, format = '%(levelname)s: %(message)s')
# ------ 取得 NAS 帳號密碼副程式 -------------------------------------------------------
def get_nasconfig():
    try:
        with open(os.path.expanduser(r'~/.nas/account')) as f:
            nasConfig = json.load(f)
    except FileNotFoundError:
        logging.warning('=== 無法找到你的 NAS 使用者帳號與密碼的設定檔: account.(txt)。 ===')
        logging.warning('=== 請新增該設定檔, 位於 使用者帳號/.nas/account 格式為: { "account":"username", "password":"********", "ip":"10.0.0.100", "port":"5000" }。 ===')
        return None
    else:
        return nasConfig        

# ------ 啟始 NAS 物件並登入帳號密碼 -----------------------------------------------------
class nasDiskStation:
    def __init__(self, nasConfig):
        self.ip = nasConfig['ip'] if nasConfig['ip'] else '10.0.0.100'
        self.port = int(nasConfig['port']) if nasConfig['port'] else 5000
        self.account = nasConfig['account'] if nasConfig['account'] else None
        self.password = nasConfig['password'] if nasConfig['password'] else None
        self.name =  'DiskStation'        
        self.base_dir = '/home'
        self.base_url = 'http://{}:{}/webapi/'.format(self.ip, self.port)
        self.auth_url = urljoin(self.base_url, 'auth.cgi')
        self.auth_params = {
            'api': 'SYNO.API.Auth',
            'version': '6',
            'method': 'login',
            'account': self.account,
            'passwd': self.password ,
            'session': self.name,
            'format': 'sid'
            }
        logging.debug('===  正在執行:diskstation.login ===')
        logging.debug('===  參數: %s, %s ===' % (self.auth_url, self.auth_params))
        try:
            response = requests.get(
                self.auth_url,
                params=self.auth_params,
                verify=False).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            self.login = None
        else:
            self.login = response['success']    
            self.sid = response['data']['sid']
            self.folder = None
            self.file = None
            self.path = None
            self.designated = None

# ------ 建立 NAS 中 DownloadStation 的 createTask 方法 -----------------------------
    def logout(self):
        self.name =  'DiskStation'        
        self.base_url = 'http://{}:{}/webapi/'.format(self.ip, self.port)
        self.auth_url = urljoin(self.base_url, 'auth.cgi')
        self.auth_params = {
            'api': 'SYNO.API.Auth',
            'version': '6',
            'method': 'logout',
            'session': self.name,
            }
        logging.debug('=== 正在執行:diskstation.logout ===')
        logging.debug('=== 參數: %s, %s ===' % (self.auth_url, self.auth_params))        
        try:
            response = requests.get(
                self.auth_url,
                params=self.auth_params,
                verify=False).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:
            return response['success']  

# ------ 建立 NAS 中 FileStation 的 createFolder 方法 -------------------------------
    def createFolder(self, designated):
        self.name = 'FileStation'
        self.folder = designated
        self.crtfdr_url = urljoin(self.base_url, 'entry.cgi')
        self.crtfdr_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='CreateFolder'),
            'version': '2',
            'method': 'create',
            'folder_path': [self.base_dir],
            'name': [designated],
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:filestation.createFolder ===')
        logging.debug('=== 參數: %s, %s ===' % (self.crtfdr_url, self.crtfdr_params))
        try:              
            response = requests.get(
                self.crtfdr_url, params=self.crtfdr_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:              
            return response['success']          

# ------ 建立 NAS 中 DownloadStation 的 createTask 方法 -----------------------------
    def createTask(self, task_uri):
        self.name = 'DownloadStation'
        self.file = task_uri
        self.path = self.base_dir + '/' + self.folder if self.folder else self.base_dir
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'create',
            'uri': self.file,
            'destination': self.path.lstrip('/'),
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.createTask ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:        
            return response['success']

# ------ 建立 NAS 中 DownloadStation 的 listTask 方法 -----------------------------
    def listTask(self):
        self.name = 'DownloadStation'
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'list',
            'additional': 'detail,transfer,file',
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.listTask ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))        
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:        
            if response['success']:
                return response['data']['tasks']
            else:
                return None

# ------ 建立 NAS 中 DownloadStation 的 deleteTask 方法 -----------------------------
    def deleteTask(self, taskids):
        self.name = 'DownloadStation'
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'delete',
            'id': ','.join(taskids), 
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.deleteTask ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))            
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:        
            return response['success']

# ------ 建立 NAS 中 DownloadStation 的 getInfo 方法 -----------------------------
    def getInfo(self, taskids):
        self.name = 'DownloadStation'
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'getinfo',
            'id': ','.join(taskids),
            'additional': 'detail,transfer,file',
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.getInfo ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))             
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:        
            if response['success']:
                return response['data']['tasks']
            else:
                return None   

# ------ 建立 NAS 中 DownloadStation 的 pauseTask 方法 -----------------------------
    def pauseTask(self, taskids):
        self.name = 'DownloadStation'
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'pause',
            'id': ','.join(taskids),
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.pauseTask ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))             
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:            
            if response['success']:
                return response['data']
            else:
                return None                

# ------ 建立 NAS 中 DownloadStation 的 resumeTask 方法 -----------------------------
    def resumeTask(self, taskids):
        self.name = 'DownloadStation'
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'resume',
            'id': ','.join(taskids),
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.resumeTask ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))             
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:            
            if response['success']:
                if response['data']['error'] == 0:
                    return True
                else:
                    return response['data']['error']        

# ------ 建立 NAS 中 DownloadStation 的 editTask 方法 -----------------------------
    def editTask(self, taskids, designated):
        self.name = 'DownloadStation'
        self.task_url = urljoin(self.base_url, self.name + '/task.cgi')
        self.designated = designated if designated else self.base_dir
        self.task_params = {
            'api': 'SYNO.{n}.{m}'.format(n=self.name, m='Task'),
            'version': '3',
            'method': 'edit',
            'id': ','.join(taskids),
            'destination': self.designated.lstrip('/'),
            '_sid': self.sid
            }
        logging.debug('=== 正在執行:downloadstation.editTask ===')
        logging.debug('=== 參數: %s, %s ===' % (self.task_url, self.task_params))             
        try:            
            response = requests.get(
                self.task_url, params=self.task_params).json()
        except TimeoutError:
            logging.error('=== 連線的主機無法回應，連線嘗試失敗。 ===')
            return None
        else:            
            if response['success']:
                if response['data']['error'] == 0:
                    return True
                else:
                    return response['data']['error']     

def appProcedure():
    listedTasks = ds214se.listTask()
    downloadingTasks = []
    finishedTasks = []
    finishingTasks = []
    pausedTasks = []
    waitingTasks = []
    errorTasks = []
    otherTasks = []
    timenow = datetime.now()
    ## 狀態有: 'status': 'downloading', 'error', 'paused', 'finished', 'waiting', 'finishing' 或 task['status_extra']['error_detail'] == 'broken_link' 
    for i in listedTasks:
        if i['status'] == 'downloading':                
            downloaded = int(i['additional']['transfer']['downloaded_pieces'])  # 已下載了 
            speed = int(i['additional']['transfer']['speed_download'])  # 每秒傳輸率 n byte
            elapsed = round(((timenow - datetime.fromtimestamp(int(i['additional']['detail']['started_time']))).days + ((timenow - datetime.fromtimestamp(int(i['additional']['detail']['started_time']))).seconds /86400)), 5)  # 已經開始下載經過 n.m 天了
            size = round(int(i['size']) / 1073741824, 3)  # 檔案大小 n GB
            percentage = round(downloaded / int(i['additional']['detail']['total_pieces']), 3) if downloaded != 0 else 0  # 已下載的百分比率
            expected = round((speed * 60 * 60 * 24) / 1073741824, 3) if speed != 0 else 0  # 按目前速率預期一天應可以下載 n GB
            downloads = round(size * percentage, 3)
            actual = round(downloads / elapsed, 3)  # 按目前速率實際一天可以下載 n GB 
            ratio = round(actual / expected, 3) if speed != 0 else 0  # 實際/預期 比率, 愈高代表過去效率愈高
            downloadingTasks.append({
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'], 
                'elapsed' : elapsed,
                'size' : size,
                'download' : downloads,
                'speed' : speed,
                'percentage' : percentage,
                'expected' : expected,
                'actual' : actual,
                'ratio' : ratio,
                'seeders' : i['additional']['detail']['connected_seeders'],                    
                'folder' : i['additional']['detail']['destination'] })  
        elif i['status'] == 'finished':
            completed = round(((timenow - datetime.fromtimestamp(int(i['additional']['detail']['completed_time']))).days + ((timenow - datetime.fromtimestamp(int(i['additional']['detail']['completed_time']))).seconds /86400)), 5)  # 已完成了 n.m 天
            finishedTasks.append({
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'],
                'completed' : completed,
                'folder' : i['additional']['detail']['destination'] })  
        elif i['status'] == 'paused':
            pausedTasks.append({
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'],
                'folder' : i['additional']['detail']['destination'] })  
        elif i['status'] == 'waiting':
            elapsed = round(((timenow - datetime.fromtimestamp(int(i['additional']['detail']['create_time']))).days + ((timenow - datetime.fromtimestamp(int(i['additional']['detail']['create_time']))).seconds /86400)), 5)  # 已等待了 n.m 天
            waitingTasks.append({
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'],
                'elapsed' : elapsed,
                'folder' : i['additional']['detail']['destination'] })
        elif i['status'] == 'error':
            errorTasks.append({
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'],
                'extra' : i['status_extra']['error_detail'],                    
                'folder' : i['additional']['detail']['destination'] })
        elif i['status'] == 'finishing':
            finishingTasks.append({
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'],                  
                'folder' : i['additional']['detail']['destination'] })                    
        else:
            otherTasks.append({
                'status': i['status'],
                'id' : i['id'],
                'title' : i['title'],
                'type' : i['type'],                    
                'folder' : i['additional']['detail']['destination'] })
    listedTasksTotal = len(listedTasks)
    del listedTasks                
    downloadingTasks.sort(key = lambda s: s['ratio'])
    from pprint import pprint
    print('全部數量: %s 個. ' % listedTasksTotal)
    if downloadingTasks:
        print('下載中: %s 個. ' % len(downloadingTasks))            
        pprint(downloadingTasks)
    if finishedTasks:
        print('已完成: %s 個. ' % len(finishedTasks))
        pprint(finishedTasks)
    if finishingTasks:
        print('正在完成: %s 個. ' % len(finishingTasks))
        pprint(finishingTasks)        
    if pausedTasks:
        print('暫停中: %s 個. ' % len(pausedTasks))
        pprint(pausedTasks)
    if waitingTasks:
        print('等待中: %s 個. ' % len(waitingTasks))
        pprint(waitingTasks)             
    if errorTasks:
        print('有錯誤: %s 個. ' % len(errorTasks))            
        pprint(errorTasks)
    if otherTasks:
        print('其他未知: %s 個. ' % len(otherTasks))            
        pprint(otherTasks)
  
# ------ 主程式 ------------------------------------------------------------------
if __name__ == '__main__':
    nasConfig = get_nasconfig()
    if nasConfig:
        # ------ 啟始並登入 ------
        ds214se = nasDiskStation(nasConfig)
        if ds214se.login:      
            logging.info('=== 登入 %s 成功! === ' % ds214se.name)
            logging.debug('=== 工作階段 (Session ID) 為 %s ===' % ds214se.sid)
            # ------ 主功能 ------
            appProcedure()
            # ------ 登出 ------
            if not ds214se.logout():
                logging.error('=== 登出 %s 失敗! == '  % ds214se.name)
            else:
                logging.info('=== 已成功登出 %s! == ' % ds214se.name)  
        else:
            logging.error('=== 登入 %s 失敗! === ' % ds214se.name)