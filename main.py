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
    "GUI notification"
    xbmc.executebuiltin(b(u('XBMC.Notification(Info:,'+message+',2000,'+icon+')')))

from contextlib import contextmanager
@contextmanager
def busy():
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    try:
        yield
    finally:
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

def kodi_link(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def apiurl(unsafe):
    return urlMain+quote(b(unsafe))

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
    result = session.get(urlMain+'/api/rest/User/login', data=dict(
        user = username,
        passwd = password,
    ))
    log(_('Login result: {}', result.json()))

    cookiejar.save(cookieFile, ignore_discard=True, ignore_expires=True)

    return session

def api(url):
    session=login()
    response = session.get(urlMain+'/api/rest/'+url).json()
    # TODO: Serious error handling
    if response.get('errors'):
        log(_('Errors: {}', response['errors']))
    return response['response']['data']

categories = [
    dict(
        title=_("Series"),
        action='series_list',
        thumb=icon,
        fanart=icon,
        plot="Todas las series disponibles",
    ),
]


def listing(title, items, item_processor):
    #log(_("{} {}", item_processor.__name__, items[0]))
    # Location step
    xbmcplugin.setPluginCategory(_handle, title)
    # Inform the skin of the kind of media
    xbmcplugin.setContent(_handle, 'videos')

    for item in items:
        item_processor(item)

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

def category_list():
    listing(
        title = _("Mediateca"),
        items = categories,
        item_processor = category_item,
        )

def series_list():
    listing(
        title = _("Series"),
        items = api('Series/listaCompleta'),
        item_processor = serie_item,
    )

def season_list(serie):
    seasons = api('Serie/temporadasSerie/'+serie)
    listing(
        title = seasons[0]['Serie'],
        items = seasons,
        item_processor = season_item,
    )

def episode_list(serie, season):
    episodes = api('Serie/capitulosSerie/'+serie+'/'+season)
    listing(
        title = episodes[0]['Serie'],
        items = episodes,
        item_processor = episode_item,
    )

def category_item(category):
    # Create a list item with a text label and a thumbnail image.
    title = category['title']
    list_item = xbmcgui.ListItem(label=title)
    # For available properties see the following link:
    # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
    # 'mediatype' is needed for a skin to display info for this ListItem correctly.
    list_item.setInfo('video', dict(category,
        mediatype = 'video',
    ))
    list_item.setArt(dict(category,
    ))
    url = kodi_link(action=category['action'])
    # Add our item to the Kodi virtual folder listing.
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)
    return list_item


def statusString(item):
    stateId = item.get("Estado",'0')
    stateText = {
        "1": _("En emision"),
        "2": _("Esperando temporada"),
        "3": _("Finalizada"),
        "4": _("Cancelada"),
    }.get(stateId)
    return stateText

def l(item, key):
    string = item.get(key) or ''
    result = [x.strip() for x in string.split(',') ]
    return result


def serie_item(serie):
    # Create a list item with a text label and a thumbnail image.
    if serie['Retirada'] == '1': return None
    if serie['Activo'] != '1': return None

    title = serie['Serie']
    list_item = xbmcgui.ListItem(label=title)
    # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
    # Here we use the same image for all items for simplicity's sake.
    # In a real-life plugin you need to set each image accordingly.
    mediaBase = quote(b(serie['Poster'][:-len('/cover.jpg')]))
    list_item.setArt(dict(
        thumb = apiurl(serie['Poster']),
        poster = apiurl(serie['Poster']),
        cover = apiurl(serie['Poster']),
        fanart = apiurl(serie['Poster'][:-len('/cover.jpg')]+'/fanart.jpg'),
    ))
    list_item.setInfo('video', dict(
        title = title,
        rating = serie['Rating'],
        tvshowtitle = serie['Serie'],
        mediatype = 'serie',
        year = int(serie['Año']),
        plot = serie['Sipnosis'], # Misspelled in db
        playcount = serie.get('VecesVisto'),
        cast = l(serie, 'Reparto'),
        director = l(serie, 'Director'),
        studio = l(serie, 'Productora'),
        writer = l(serie, 'Guion'),
        dateadded = serie.get('FechaAñadido'),
        status = statusString(serie),
    ))
    url = kodi_link(action='season_list', serie=serie['IdSerie'])
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
    list_item.setArt(dict(
        thumb = apiurl(season['Poster']),
        poster = apiurl(season['Poster']),
        cover = apiurl(season['Poster']),
        fanart = apiurl(season['Poster'][:-len('/cover.jpg')]+'/fanart.jpg'),
    ))
    list_item.setInfo('video', dict(
        title = title,
        rating = season['Rating'],
        tvshowtitle = season['Serie'],
        mediatype = 'season',
        year = int(season['Año']),
        season = int(season['Temporada']),
        plot = season['Sipnosis'], # Misspelled in db
        playcount = season.get('VecesVisto'),
        cast = l(season, 'Reparto'),
        director = l(season, 'Director'),
        studio = l(season, 'Productora'),
        writer = l(season, 'Guion'),
        dateadded = season.get('FechaAñadido'),
        status = statusString(season),
    ))
    url = kodi_link(action='episode_list', serie=season['IdSerie'], season=season['Temporada'])
    # Add our item to the Kodi virtual folder listing.
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

def episode_item(episode):
    if episode['Retirada'] == '1': return None
    if episode['Activo'] != '1': return None

    title = _("{Temporada}x{Capitulo} - {Titulo}", **episode)
    mediaBase = quote(b(episode['Fichero'][:-len('.mp4')]))

    list_item = xbmcgui.ListItem(label=title)
    list_item.setArt(dict(
        thumb = apiurl(episode['Fichero'][:-len('.mp4')]+'.jpg'),
        poster = apiurl(episode['Fichero'][:-len('.mp4')]+'.jpg'),
        cover = apiurl(episode['Fichero'][:-len('.mp4')]+'.jpg'),
        fanart = apiurl(episode['Fichero'][:-len('.mp4')]+'.jpg'),
    ))
    list_item.setInfo('video', dict(
        originaltitle = episode['Titulo'],
        title = title,
        rating = episode['Rating'],
        tvshowtitle = episode['Serie'],
        mediatype = 'episode',
        year = int(episode['Año']),
        season = int(episode['Temporada']),
        episode = episode['Capitulo'],
        plot = episode['Sipnosis'], # Misspelled in db
        playcount = episode.get('VecesVisto'),
        cast = l(episode, 'Reparto'),
        director = l(episode, 'Director'),
        studio = l(episode, 'Productora'),
        writer = l(episode, 'Guion'),
        dateadded = episode.get('FechaAñadido'),
        status = statusString(episode),
    ))
    list_item.setProperty('IsPlayable', 'true')
    url = kodi_link(action='play_video', url=apiurl(episode['Fichero']))
    # Add our item to the Kodi virtual folder listing.
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=False)


def play_video(url):
    """
    Play a video by the provided url.

    :param url: Fully-qualified video URL
    :type url: str
    """
    # Create a playable item with a url to play.
    play_item = xbmcgui.ListItem(path=url)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

entrypoints = [
    series_list,
    category_list,
    season_list,
    episode_list,
    play_video,
]

log('\nRunning {}'.format(" ".join(sys.argv)))


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    params = dict(parse_qsl(paramstring))

    action = params.pop('action','category_list')

    dispatchers = { fun.__name__: fun for fun in entrypoints}
    dispatcher = dispatchers.get(action, None)
    if not dispatcher:
        raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    dispatcher(**params)

if __name__ == '__main__':
    # Params are urlencoded as the second parameter
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])


# vim: et
