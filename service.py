import os
import sys
import time
import xbmc
import xbmcaddon
import json
import urllib2
from urllib import quote_plus
from traceback import print_exc

try:
	from sqlite3 import dbapi2 as sqlite
	xbmc.log("XBLFriends: Loading sqlite3 as DB engine")
except:
	from pysqlite2 import dbapi2 as sqlite
	xbmc.log("XBLFriends: Loading pysqlite2 as DB engine")

ADDON = xbmcaddon.Addon(id='service.XBLFriends')
DB = xbmc.translatePath(os.path.join(ADDON.getAddonInfo('profile'), 'XBLFriends.db'))

class XBLMonitor: 
	def __init__(self):
		self.last_run = 0
		self.rate_limit = 150
		self.current_rate = 0
		self.seconds = 180
		self.gamerTag = ADDON.getSetting('gamertag')
		self.idle_timeout = ADDON.getSetting('idle_timeout')

	def do_notifications(self, data):
		if not os.path.isdir(os.path.dirname(DB)):
			os.makedirs(os.path.dirname(DB))
		db = sqlite.connect(DB)
		db.execute('CREATE TABLE IF NOT EXISTS friends (friend UNIQUE, status)')
		db.commit()
		for friend in data['Friends']:
			status = db.execute('SELECT status FROM friends WHERE friend=?', (friend['GamerTag'],))
			status = status.fetchone()
			if status and (status[0] == friend['IsOnline']): continue
			else:
				db.execute('INSERT OR REPLACE INTO friends (friend,status) VALUES(?,?)', (friend['GamerTag'], friend['IsOnline']))
				db.commit()
				if friend['IsOnline']:
					builtin = "XBMC.Notification(%s,%s,5000,%s)" %(friend['GamerTag'],friend['Presence'],friend['LargeGamerTileUrl'])
					builtin = builtin.encode('utf-8')
					xbmc.executebuiltin(builtin)
					xbmc.log('XBLFriends: %s is Online' %friend['GamerTag'])
					xbmc.sleep(5000)
		db.close()

	def check_run_conditions(self):
		#Update in case things have changed since last check
		self.gamerTag = ADDON.getSetting('gamertag')
		self.idle_timeout = ADDON.getSetting('idle_timeout')
		
		#Is monitoring enabled?
		if ADDON.getSetting('enable') =='false':
			xbmc.log('XBLFriends: Monitoring disabled')
			return False

		#Do we have a gamerTag set?
		if not self.gamerTag:
			xbmc.log('XBLFriends: No gamerTag set')
			return False

		#Are we still under the rate limit?
		if int(self.current_rate) > int(self.rate_limit):
			xbmc.log('XBLFriends: Rate limit exceeded. Limit: %s Current: %s' %(self.rate_limit, self.current_rate))
			return False
		
		if xbmc.getGlobalIdleTime() > self.idle_timeout:
			xbmc.log('XBLFriends: XBMC is idle. Not fetching data. idle_timeout: %s' %self.idle_timeout, level=xbmc.LOGDEBUG)
			return False
		return True
		
	def get_friends(self):
		url = 'https://xboxapi.com/index.php/json/friends/%s' %quote_plus(self.gamerTag)
		req = urllib2.Request(url)
			#Identify ourselves
		req.add_header('User-agent', 'XBLFriends service for XBMC')
		data = urllib2.urlopen(req)
		data = json.load(data)
			#set the current and limit rates as reported by the server
		self.current_rate, self.rate_limit = data['API_Limit'].split("/")
		return data

	def clear_status(self):
		try:
			db = sqlite.connect(DB)
			db.execute('UPDATE friends SET status = 0')
			db.commit()
			db.close()
		except:
			xbmc.log('XBLFriends: Failed to reset status')
			print_exc()

	def runProgram(self):
		if ADDON.getSetting('startup_notify') =='true':
			self.clear_status()
		while not xbmc.abortRequested:
			now = time.time()
			if now > (self.last_run + self.seconds) and self.check_run_conditions():
				try:
					data = self.get_friends()
				except urllib2.URLError:
					data = {'Success':False, 'Reason':'Failed to connect to url'}
						#In effect, wait 1 minute and try again.
					self.last_run = self.last_run - 120
					print_exc()

				if data['Success']:
					self.do_notifications(data)
					self.last_run = now
				else: xbmc.log('XBLFriends: API call failed. Data: %s' %data)

			xbmc.sleep(1000)
		xbmc.log('XBLFriends: Notification service ending...')

def get_params():
	param={}
	paramstring=sys.argv[len(sys.argv)-1]
	if len(paramstring)>=2:
		cleanedparams=paramstring.replace('?','')
		if (paramstring[len(paramstring)-1]=='/'):
				paramstring=paramstring[0:len(paramstring)-2]
		pairsofparams=cleanedparams.split('&')
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]			
	return param

mode = get_params().get('mode', None)
monitor = XBLMonitor()

if mode == 'ondemand':
	xbmc.log('XBLFriends: Running on demand')
	monitor.clear_status()
	if int(monitor.current_rate) < int(monitor.rate_limit):
		data = monitor.get_friends()
		monitor.do_notifications(data)
	else:
		xbmc.log('XBLFriends: Rate limit exceeded. Limit: %s Current: %s' %(monitor.rate_limit, monitor.current_rate))
else:
	xbmc.log('XBLFriends: Notification service starting...')
	monitor.runProgram()