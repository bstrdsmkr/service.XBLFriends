import os
import time
import xbmc
import xbmcaddon
import json
import urllib2

try:
	from sqlite3 import dbapi2 as sqlite
	xbmc.log("XBLFriends: Loading sqlite3 as DB engine")
except:
	from pysqlite2 import dbapi2 as sqlite
	xbmc.log("XBLFriends: Loading pysqlite2 as DB engine")

ADDON = xbmcaddon.Addon(id='service.XBLFriends')
DB = xbmc.translatePath(os.path.join(ADDON.getAddonInfo('profile'), 'XBLFriends.db'))

class XBLMonitor:             
	def runProgram(self):
		self.last_run = 0
		seconds = 180
		if ADDON.getSetting('startup_notify') =='true':
			try:
				db = sqlite.connect(DB)
				db.execute('UPDATE friends SET status = 0')
				db.commit()
				db.close()
			except:
				xbmc.log('XBLFriends: Failed to reset status at startup')
		while not xbmc.abortRequested:
			if ADDON.getSetting('enable') =='true':
				now = time.time()
				if now > (self.last_run + seconds):
					gamerTag = ADDON.getSetting('gamertag')
					url = 'https://xboxapi.com/index.php/json/friends/%s' %gamerTag
					try:
						data = urllib2.urlopen(url)
						data = json.load(data)
					except:
						data = {'Success':False, 'Reason':'Failed to connect to url'}
						self.last_run = self.last_run - 120 #In effect, wait 1 minute and try again.
					if data['Success']:
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
						db.close()
						self.last_run = now
					else: xbmc.log('XBLFriends: API call failed. Data: %s' %data)
			else:
				xbmc.log('XBLFriends: Monitoring disabled')
				break
			xbmc.sleep(1000)
		xbmc.log('XBLFriends: Notification service ending...')

xbmc.log('XBLFriends: Notification service starting...')
XBLMonitor().runProgram()