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
		while not xbmc.abortRequested:
			if ADDON.getSetting('enable') =='true':
				now = time.time()
				if now > (self.last_run + seconds):
					gamerTag = ADDON.getSetting('gamertag')
					url = 'https://xboxapi.com/index.php/json/friends/%s' %gamerTag
					data = json.load(urllib2.urlopen(url))
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