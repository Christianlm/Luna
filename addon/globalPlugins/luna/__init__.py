# -*- coding: UTF-8 -*-

# Luna v. 0.3.20210711-dev add-on for NVDA SCREEN READER.
# Last update 18 august 2020.
# Copyright (C) 2020 by Chris Leo <llajta2012ATgmail.com>
# Released under GPL 2
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import addonHandler
import globalPluginHandler
import glob
import globalVars
import os
import ui
import scriptHandler
from scriptHandler import script
from urllib.request import urlopen as uReq
import sys
BS_DIR = os.path.dirname(__file__)
libs = os.path.join(BS_DIR, "library")
sys.path.append(libs)
from bs4 import BeautifulSoup as soup
sys.path.remove(libs)

addonHandler.initTranslation()

ADDON_SUMMARY = addonHandler.getCodeAddon().manifest["summary"]

memo = ""

def getMoonInfo():
	moon_url = "http://www.calendario-365.it/luna/posizione-odierna-della-Luna.html"
	uClient = uReq(moon_url)
	page_html = uClient.read()
	uClient.close()
	page_soup = soup(page_html, "html.parser")
	containers = page_soup.findAll("div",{"class":"panel panel-primary"})
	for container in containers:
			shipping_container = container.findAll("div",{"class":"fl"})
			return shipping_container

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	try:
		scriptCategory = unicode(ADDON_SUMMARY)
	except NameError:
		scriptCategory = str(ADDON_SUMMARY)

	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)

	@script(
		# Translators: Message presented in input help mode.
		description=_("Retrieves moon fase."),
	)
	def script_moonFase(self, gesture):
		shipping_container = getMoonInfo()
		moonFase = shipping_container[7].text
		percentage = shipping_container[9].text
		ui.message(moonFase + percentage + _("visibility"))

	@script(
		# Translators: Message presented in input help mode.
		description=_("Announces informations about the moon."),
	)
	def script_moonPosition(self, gesture):
		global memo
		shipping_container = getMoonInfo()
		dateHours = shipping_container[1].text
		distance = shipping_container[3].text
		age = shipping_container[5].text
		moonFase = shipping_container[7].text
		percentage = shipping_container[9].text
		memo = (_("Moon phase of ") + dateHours + ": " + moonFase + _(". distance: ") + distance + _(". Visibility: ") + percentage + _(". Moon age: ") + age)
		ui.message(memo)

	# Script to retrieve the last moon info .
	@script(
		# Translators: Message presented in input help mode.
		description=_("Retrieves the last moon information."),
	)
	def script_lastControl(self, gesture):
		if memo:
			# Translators: title of browseable message box.
			ui.browseableMessage(".\n".join(memo.split(". ")), _("Moon Position"))
		else:
			#translators: message when  there are no recent info about the moon.
			ui.message(_("There is no recent info for moon position."))
