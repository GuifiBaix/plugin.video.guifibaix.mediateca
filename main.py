# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
"""
Guifibaix Mediateca  plugin

"""

# Python 2 compatibility, remove when unneeded
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()

import sys
import os
try:
    from urllib.parse import urlencode, parse_qsl, quote
except ImportError:
    from urllib import urlencode
    from urlparse import parse_qsl, quote
import xbmcgui
import xbmcplugin
import xbmcaddon

def u(text):
    if type(text)==type(u''): return text
    if type(text)==type(b''): return text.decode('utf8')
    return type('u')(text)

def b(text):
    if type(text)==type(b''): return text
    if type(text)==type(u''): return text.encode('utf8')
    return type('u')(text).encode('utf8')

def _(text, *args, **kwds):
    # TODO: translate
    return u(text).format(*args, **kwds)

def dumphash(content):
    return
    import hashlib
    import io
    md5 = hashlib.sha1()
    md5.update(b(content))
    filename = u'dump_{}.html'.format(md5.hexdigest())
    with io.open(filename, 'w', encoding='utf8') as f:
        f.write(content)
    return filename

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon()
addonID = addon.getAddonInfo('id')
addonFolder = u(xbmc.translatePath('special://home/addons/'+addonID))
addonUserDataFolder = u(xbmc.translatePath("special://profile/addon_data/"+addonID))
urlMain = addon.getSetting('baseurl')
cookieFile = os.path.join(addonUserDataFolder, "mediateca.cookies")

icon = os.path.join(addonFolder, "icon.png")
def notify(message):
    xbmc.executebuiltin(b(u('XBMC.Notification(Info:,'+message+',2000,'+icon+')')))
def startBusy():
    xbmc.executebuiltin('ActivateWindow(busydialog)')
def endBusy():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
def log(msg, level=xbmc.LOGNOTICE):
    # xbmc.log('%s: %s' % (addonID, msg), level)
    log_message = u'{0}: [{2}] {1}'.format(addonID, msg, _handle)
    xbmc.log(b(log_message), level)
    """
    xbmc.LOGDEBUG = 0
    xbmc.LOGERROR = 4
    xbmc.LOGFATAL = 6
    xbmc.LOGINFO = 1
    xbmc.LOGNONE = 7
    xbmc.LOGNOTICE = 2
    xbmc.LOGSEVERE = 5
    xbmc.LOGWARNING = 3
    """

log('\nRunning {}'.format(" ".join(sys.argv)))


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))

import requests
import cookielib
import urllib2
cookiejar = cookielib.MozillaCookieJar()
userAgent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2566.0 Safari/537.36"

def deleteCookies():
    if os.path.exists(cookieFile):
        os.remove(cookieFile)

def requestPassword():
    password = ''
    keyboard = xbmc.Keyboard('', _("Password:"), True)
    keyboard.setHiddenInput(True)
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        password = keyboard.getText()
    return password and u(password)

def requestUsername(username=None):
    keyboard = xbmc.Keyboard(username or '', _('GuifiBaix user name'))
    keyboard.doModal()
    if keyboard.isConfirmed() and u(keyboard.getText()):
        return u(keyboard.getText())

def retrieveOrAskAuth():
    username = addon.getSetting('username')
    password = addon.getSetting('password')

    if not username or not password:
        username = requestUsername(username)

    if password:
        password = u(password)

    if not password:
        password = requestPassword()

    addon.setSetting('username', username)
    addon.setSetting('password', password)
    return username, password

def login(retry=False):

    username, password = retrieveOrAskAuth()

    session = requests.Session()
    session.cookies = cookiejar
    result = session.post(urlMain+'/api/rest/User/login', data=dict(
        user = username,
        passwd = password,
    ))
    log(result.json())

    cookiejar.save(cookieFile, ignore_discard=True, ignore_expires=True)

    return session

def api(url):
    session=login()
    response = session.get(urlMain+'/api/rest/'+url).json()
    # TODO: Error handling
    return response['response']['data']


def series_list():
    """
    List of series
    """
    series = api('Series/listaCompleta')

    # Location step
    xbmcplugin.setPluginCategory(_handle, 'Series')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')

    for serie in series:
        serie_item(serie)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def season_list(serie):
    seasons = api('Serie/temporadasSerie/'+serie)

    for season in seasons:
        season_item(season)

    # Location step
    xbmcplugin.setPluginCategory(_handle, seasons[0]['Serie'])
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

def episode_list(serie, season):
    episodes = api('/Serie/capitulosSerie/'+serie+'/'+season)

    for episode in episodes:
        episode_item(episode)

    # Location step
    xbmcplugin.setPluginCategory(_handle, episodes[0]['Serie'])
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def serie_item(serie):
    # Create a list item with a text label and a thumbnail image.
    if serie['Retirada'] == '1': return None
    if serie['Activo'] != '1': return None

    title = serie['Serie']
    title_path = quote(b(title.replace("'","")))
    list_item = xbmcgui.ListItem(label=title)
    # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
    # Here we use the same image for all items for simplicity's sake.
    # In a real-life plugin you need to set each image accordingly.
    mediaBase = quote(b(serie['Poster'][:-len('/cover.jpg')]))
    if mediaBase != '/Series/' + title_path:
        log("{} {}".format(title_path, mediaBase))
    list_item.setArt(dict(
        poster = urlMain+mediaBase+'/cover.jpg',
        thumb = urlMain+mediaBase+'/cover.jpg',
        cover = urlMain+mediaBase+'/cover.jpg',
        fanart = urlMain+mediaBase+'/fanart.jpg',
    ))
    # For available properties see the following link:
    # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
    # 'mediatype' is needed for a skin to display info for this ListItem correctly.
    list_item.setInfo('video', {
        'title': title,
        'genre': title,
        'mediatype': 'video',
    })
    url = get_url(action='season_list', serie=serie['IdSerie'])
    # is_folder = True means that this item opens a sub-list of lower level items.
    is_folder = True
    # Add our item to the Kodi virtual folder listing.
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)
    return list_item


def season_item(season):
    # Create a list season with a text label and a thumbnail image.

    if season['Retirada'] == '1': return None
    if season['Activo'] != '1': return None

    title = _("Temporada {}", season['Temporada'])
    mediaBase = quote(b(season['Ruta']))

    list_item = xbmcgui.ListItem(label=title)
    # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list season.
    # Here we use the same image for all items for simplicity's sake.
    # In a real-life plugin you need to set each image accordingly.
    list_item.setArt(dict(
        poster = urlMain+mediaBase+'/cover.jpg',
        thumb = urlMain+mediaBase+'/cover.jpg',
        cover = urlMain+mediaBase+'/cover.jpg',
        fanart = urlMain+mediaBase+'/fanart.jpg',
    ))
    # For available properties see the following link:
    # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
    # 'mediatype' is needed for a skin to display info for this ListItem correctly.
    list_item.setInfo('video', {
        'title': title,
        'genre': title,
        'mediatype': 'video',
    })
    url = get_url(action='episode_list', serie=season['IdSerie'], season=season['Temporada'])
    # is_folder = True means that this season opens a sub-list of lower level items.
    is_folder = True
    # Add our item to the Kodi virtual folder listing.
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

def episode_item(episode):
    if episode['Retirada'] == '1': return None
    if episode['Activo'] != '1': return None

    title = _("{Temporada}x{Capitulo} - {Titulo}", **episode)
    mediaBase = quote(b(episode['Fichero'][:-len('.mp4')]))

    list_item = xbmcgui.ListItem(label=title)
    # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list .
    # Here we use the same image for all items for simplicity's sake.
    # In a real-life plugin you need to set each image accordingly.
    list_item.setArt(dict(
        poster = urlMain+mediaBase+'.jpg',
        thumb = urlMain+mediaBase+'.jpg',
        cover = urlMain+mediaBase+'.jpg',
    ))
    # Set additional info for the list item.
    # 'mediatype' is needed for skin to display info for this ListItem correctly.
    list_item.setInfo('video', {
        'title': title,
        'mediatype': 'video',
    })
    # Set 'IsPlayable' property to 'true'.
    # This is mandatory for playable items!
    list_item.setProperty('IsPlayable', 'true')
    url = get_url(action='play', video=urlMain+quote(b(episode['Fichero'])))
    # Add the list item to a virtual Kodi folder.
    is_folder = False
    # Add our item to the Kodi virtual folder listing.
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=False)


def play_video(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        action = params['action']

        if action == 'season_list':
            season_list(params['serie'])

        elif action == 'episode_list':
            episode_list(params['serie'], params['season'])

        elif action == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])

        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        series_list()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])


# vim: et
