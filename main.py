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

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

addon = xbmcaddon.Addon()
addonID = addon.getAddonInfo('id')
addonFolder = u(xbmc.translatePath('special://home/addons/'+addonID))
addonUserDataFolder = u(xbmc.translatePath("special://profile/addon_data/"+addonID))
icon = os.path.join(addonFolder, "icon.png")

urlMain = addon.getSetting('baseurl') # mediateca base url


# https://kodi.wiki/view/Artwork_types
artwork_tags = [
    'thumb',
    'poster',
    'banner',
    'fanart',
    'clearart',
    'clearlogo',
    'landscape',
    'icon',
]

# https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
video_info_tags = [
    'genre',
    'country',
    'year',
    'episode',
    'season',
    'sortepisode',
    'sortseason',
    'episodeguide',
    'showlink',
    'top250',
    'setid',
    'tracknumber',
    'rating',
    'userrating',
    'watched',
    'playcount',
    'overlay',
    'cast',
    'castandrole',
    'director',
    'mpaa',
    'plot',
    'plotoutline',
    'title',
    'originaltitle',
    'sorttitle',
    'duration',
    'studio',
    'tagline',
    'writer',
    'tvshowtitle',
    'premiered',
    'status',
    'set',
    'setoverview',
    'tag',
    'imdbnumber',
    'code',
    'aired',
    'credits',
    'lastplayed',
    'album',
    'artist',
    'votes',
    'path',
    'trailer',
    'dateadded',
    'mediatype',
    'dbid',
]
def notify(message):
    "GUI notification"
    xbmc.executebuiltin(b(u('XBMC.Notification(Info,'+message+',2000,'+icon+')')))

def error(message):
    "GUI notification"
    xbmc.executebuiltin(b(u('XBMC.Notification(Error,'+message+',2000,'+icon+')')))

def fail(message):
    error(message)
    sys.exit(-1)


from contextlib import contextmanager
@contextmanager
def busy():
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialog)')

def log(msg, level=xbmc.LOGNOTICE):
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

def kodi_link(**params):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param params: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(params))

def kodi_refresh():
    xbmc.executebuiltin("Container.Refresh")

def kodi_action(**params):
    "Returns a menu entry action string to run a kodi link"

    return 'XBMC.RunPlugin({})'.format(kodi_link(**params))

def apiurl(unsafe):
    "Constructs an url to the Mediateca Api"

    return urlMain+quote(b(unsafe))

def requestUsername(username=None):
    keyboard = xbmc.Keyboard(username or '', _('GuifiBaix user name'))
    keyboard.doModal()
    if keyboard.isConfirmed() and u(keyboard.getText()):
        return u(keyboard.getText())

def requestPassword():
    password = ''
    keyboard = xbmc.Keyboard('', _("GuifiBaix Password"), True)
    keyboard.setHiddenInput(True)
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        password = keyboard.getText()
    return password and u(password)

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

class MediatecaApi(object):
    def __init__(self):
        self._token = None

    def _api_noauth(self, url, **kwds):
        import requests
        fullurl = urlMain + '/api/rest/' + url
        try:
            response = requests.post(fullurl, **kwds)
        except requests.ConnectionError as e:
            fail(_("No se puede connectar con la Mediateca"))

        try:
            result = response.json()
        except Exception as e:
            log(_("Non JSON api response:\n{}", response.text))
            fail(_("Invalid API response: {}", e))

        for k in result:
            if 'Error' in k and result[k]:
                log(_("API Prototocol Error accessing {}: {}", fullurl, result[k]))
                fail(_("API Protocol Error"))

        return result

    def __enter__(self):
        "Creates an autentication token"
        username, password = retrieveOrAskAuth()

        response = self._api_noauth('User/login/', data=dict(
            user = username,
            passwd = password,
        ))

        if response['errors']:
            fail(_("Login error: {}", '\n'.join(response['errors'])))

        self._token = response['response']['Token']
        return self

    def __exit__(self, e_typ, e_val, trcbak):
        response = self._api_noauth('User/logout', headers=dict(
            Authorization = 'Bearer ' + self._token
        ))
        if response['errors']:
            fail(_("Logout error: {}", '\n'.join(response['errors'])))

    def __call__(self, url, *args):
        url = '/'.join([url] + [u(a) for a in args])
        response = self._api_noauth(url,
            headers=dict(
                Authorization = 'Bearer '+self._token
            ) if self._token else {},
        )
        if response.get('errors'):
            fail(_('API Error: {}', response['errors'][0]))

        if 'response' not in response or 'data' not in response['response']:
            import json
            log(_('Unexpected API response:\n{}', json.dumps(response)))
            fail(_('Unexpected API response: {}'))

        return response['response']['data']

def api(url, *args):
    with MediatecaApi() as mediateca:
        return mediateca(url, *args)

categories = [
    dict(
        title=_("Episodios Pendientes"),
        action='pending_list',
        thumb='DefaultInProgressShows.png',
        fanart=icon,
        plot=_(
            "Todos los nuevos episodios de las series que sigues."
            "\n"
            "\n"
            "Para seguir una serie, "
            "usa el menu contextual con una pulsación larga."
        ),
        disabled=addon.getSetting("experimental")!='true',
    ),
    dict(
        title=_("Series"),
        action='series_list',
        thumb='DefaultTVShows.png',
        fanart=icon,
        plot="Todas las series disponibles",
    ),
    dict(
        title=_("Películas"),
        action='movie_list',
        thumb='DefaultMovies.png',
        fanart=icon,
        plot=_("Todas las películas disponibles"),
    ),
]


def buildItem(data):
    def extract(data, tags):
        return {
            tag: data.pop(tag)
            for tag in tags
            if tag in data
        }

    label = data.pop('label')
    artwork = extract(data, artwork_tags)
    info = extract(data, video_info_tags)
    menus = data.pop('menus',[])
    playable = data.pop('playable', False)

    if data:
        log(_("Un processed keys: {}", list(data.keys())))

    list_item = xbmcgui.ListItem(label=label)
    list_item.setArt(artwork)
    list_item.setInfo('video', info)
    if playable:
        list_item.setProperty('IsPlayable', 'true')
    if menus:
        list_item.addContextMenuItems(menus)

    return list_item


def listing(title, items, item_processor, content='videos', sortings=[xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]):
    """Defines a listing view depending on the parameters:
    - title: view header (pluginCategory)
    - items: items retrieved from the api to be processed
    - item_processor: a function which turns api items into kodi list items
    - content: how the skin should interpret the list: 
        - files, songs, artists, albums, movies, tvshows, episodes, musicvideos, videos, images, games 
        - See: https://codedocs.xyz/xbmc/xbmc/group__python__xbmcplugin.html#gaa30572d1e5d9d589e1cd3bfc1e2318d6
    - sortings: list of enabled sortings the user can choose:
        - empty means user cannot change the provided order
        - Available values: https://codedocs.xyz/xbmc/xbmc/group__python__xbmcplugin.html#ga85b3bff796fd644fb28f87b136025f40
    """

    # Debuging help if we missed some attribute
    items and log(_("{}, attribs from api: {}",
        item_processor.__name__,
        ', '.join(sorted(items[0]))))

    # Location step
    xbmcplugin.setPluginCategory(_handle, title)
    # Inform the skin of the kind of media
    xbmcplugin.setContent(_handle, content)

    nitems = len(items)
    for item in items:
        processed = item_processor(item)
        if not processed: continue
        isFolder = processed.pop('isfolder', True)
        url = processed.pop('target')
        li = buildItem(processed)
        xbmcplugin.addDirectoryItem(_handle, url, li, isFolder=isFolder, totalItems=nitems)

    for sorting in sortings:
        xbmcplugin.addSortMethod(_handle, sorting)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

def category_list():
    listing(
        title = _("Mediateca"),
        items = categories,
        item_processor = category_item,
        content = 'videos',
        sortings=[], # sorted as listed
        )

def movie_list():
    listing(
        title = _("Películas"),
        items = api('Peliculas/listaCompleta'),
        item_processor = movie_item,
        content = 'movies',
        sortings = [
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,
            xbmcplugin.SORT_METHOD_DATEADDED,
            xbmcplugin.SORT_METHOD_PLAYCOUNT,
            xbmcplugin.SORT_METHOD_VIDEO_YEAR,
            xbmcplugin.SORT_METHOD_VIDEO_RATING,
            xbmcplugin.SORT_METHOD_MPAA_RATING,
        ],
    )

def series_list():
    listing(
        title = _("Series"),
        items = api('Series/listaCompleta'),
        item_processor = serie_item,
        content = 'tvshows',
    )

def season_list(serie):
    seasons = api('Serie/temporadasSerie/', serie)
    listing(
        title = seasons[0]['Serie'],
        items = seasons,
        item_processor = season_item,
        content = 'tvshows',
    )

def episode_list(serie, season):
    episodes = api('Serie/capitulosSerie/', serie, season)
    listing(
        title = episodes[0]['Serie'],
        items = episodes,
        item_processor = episode_item,
        content = 'episodes',
        sortings=[
            xbmcplugin.SORT_METHOD_LABEL,
        ],
    )

def pending_list():
    episodes = api('Series/pendingEpisodes/')
    listing(
        title = _("Pending episodes"),
        items = episodes,
        item_processor = mixed_episode_item,
        sortings=[],
    )


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
    "turns a comma separated list string into an actual python list"
    string = item.get(key)
    if not string: return []
    result = [x.strip() for x in string.split(',') ]
    return result


def category_item(category):
    " Creates a category list item"

    if category.pop('disabled', False): return None

    return dict(
        category,
        label = category['title'],
        target = kodi_link(action=category.pop('action')),
    )

def serie_item(serie):
    " Creates a serie list item"

    if serie['Retirada'] == '1': return None
    if serie['Activo'] != '1': return None

    tags = []
    if serie.get("Subscribed")=='1': tags.append(_("[La sigues]"))
    tags = ' '.join(tags)
    if tags: tags+='\n\n'

    return dict(
        label = serie['Serie'],

        thumb = apiurl(serie['Poster']),
        poster = apiurl(serie['Poster']),
        fanart = apiurl(serie['Poster'][:-len('/cover.jpg')]+'/fanart.jpg'),

        title = serie['Serie'],
        rating = serie['Rating'],
        tvshowtitle = serie['Serie'],
        mediatype = 'tvshow',
        year = int(serie['Año']),
        season = int(serie['Temporadas']),
        plot = tags + serie['Sipnosis'], # Misspelled in db
        #playcount = serie.get('VecesVisto'),
        cast = l(serie, 'Reparto'),
        director = l(serie, 'Director'),
        studio = l(serie, 'Productora'),
        writer = l(serie, 'Guion'),
        country = serie.get('Pais'),
        dateadded = serie.get('FechaAñadido'),
        aired = serie.get('PrimeraEmision'),
        imdbnumber = serie.get('IMDB_ID'),
        status = statusString(serie),

        target = kodi_link(action='season_list', serie=serie['IdSerie']),
        menus = menu_follow_serie(serie['IdSerie'], wasSet = serie.get('Subscribed')=='1'),
    )

def season_item(season):
    "Creates a season list item"

    if season['Retirada'] == '1': return None
    if season['Activo'] != '1': return None

    title = _("Temporada {}", season['Temporada'])

    tags = []
    if season.get("Subscribed")=='1': tags.append(_("[La sigues]"))
    tags = ' '.join(tags)
    if tags: tags+='\n\n'

    return dict(
        label=title,

        thumb = apiurl(season['Poster']),
        poster = apiurl(season['Poster']),
        fanart = apiurl(season['Poster'][:-len('/cover.jpg')]+'/fanart.jpg'),

        title = title,
        rating = season['Rating'],
        tvshowtitle = season['Serie'],
        mediatype = 'season',
        year = int(season['Año']),
        season = int(season['Temporadas']),
        plot = tags + season['Sipnosis'], # Misspelled in db
        playcount = season.get('VecesVistoUsuario',0),
        cast = l(season, 'Reparto'),
        director = l(season, 'Director'),
        studio = l(season, 'Productora'),
        writer = l(season, 'Guion'),
        country = season.get('Pais'),
        dateadded = season.get('FechaAñadido'),
        imdbnumber = season.get('IMDB_ID'),
        status = statusString(season),

        menus = menu_follow_serie(season['IdSerie'], wasSet = season.get("Subscribed")=='1'),
        target = kodi_link(action='episode_list', serie=season['IdSerie'], season=season['Temporada'])
    )

def mixed_episode_item(episode):
    reused = episode_item(episode)
    return reused and dict(
        reused,
        title = _("{Serie}\n{Temporada}x{Capitulo} - {Titulo}", **episode),
        label = _("{Serie}\n{Temporada}x{Capitulo} - {Titulo}", **episode),
    )

def episode_item(episode):
    "Creates an episode list item"

    if episode['Retirada'] == '1': return None
    if episode['Activo'] != '1': return None


    tags = []
    if episode.get("Subscribed")=='1': tags.append(_("[La sigues]"))
    tags = ' '.join(tags)
    if tags: tags+='\n\n'

    label = _("{Temporada}x{Capitulo} - {Titulo}", **episode)

    return dict(
        label = label,

        thumb = apiurl(episode['Poster']),
        poster = apiurl(episode['Fichero'][:-len('.mp4')]+'.jpg'),
        fanart = apiurl(episode['Fichero'][:-len('.mp4')]+'.jpg'),

        title = label,
        originaltitle = episode['Titulo'],
        rating = episode['Rating'],
        tvshowtitle = episode['Serie'],
        mediatype = 'episode',
        year = int(episode['Año']),
        season = int(episode['Temporadas']),
        episode = episode['Capitulo'],
        plot = tags + episode['Sipnosis'], # Misspelled in db
        #playcount = episode.get('VecesVisto'),
        cast = l(episode, 'Reparto'),
        director = l(episode, 'Director'),
        studio = l(episode, 'Productora'),
        writer = l(episode, 'Guion'),
        country = episode.get('Pais'),
        dateadded = episode.get('FechaAñadido'),
        imdbnumber = episode.get('IMDB_ID'),
        status = statusString(episode),

        isfolder = False,
        playable = True,
        menus = menu_follow_serie(episode['IdSerie'], wasSet = episode.get("Subscribed")=='1'),
        target = kodi_link(action='play_video', url=apiurl(episode['Fichero'])),
        playable = True,
    )

def movie_item(movie):
    if movie['Activo'] != '1': return None
    if movie['MostrarEnListaCompleta'] != '1':
        return None

    title = _("[{Año}] {Titulo}", **movie)

    return dict(
        label=title,

        thumb = apiurl(movie['Poster']),
        poster = apiurl(movie['Poster']),
        fanart = apiurl(movie['Poster'][:-len('cover.jpg')]+'fanart.jpg'),

        originaltitle = movie['Titulo'],
        title = movie['Titulo'],
        rating = movie['Rating'],
        mediatype = 'movie',
        genre = ', '.join(l(movie, 'Generos')),
        year = int(movie['Año']),
        plot = movie['Sipnosis'], # Misspelled in db
        #playcount = movie.get('Visto'),
        cast = l(movie, 'Reparto'),
        director = l(movie, 'Director'),
        studio = l(movie, 'Productora'),
        writer = l(movie, 'Guion'),
        country = movie.get('Pais'),
        dateadded = movie.get('FechaAñadido'),
        imdbnumber = movie.get('IMDB_ID'),
        trailer = movie.get('Trailer'), # TODO: Not working, needs local file, url given
        status = statusString(movie),
        mpaa = movie['Clasificacion'],
        # TODO: Unused:
        # TODO: 'Clasificacion', 'ClasificacionPorEdad', 'Coleccion', 'Coleccion2'
        # TODO: 'Estilo', 'IMDB_ID', 'TMDB_ID', 'VOSE', 'Web'
        # TODO: 'IdCategoria', 'IdClasificacion', 'IdPelicula', 'Identificador',

        isfolder = False,
        playable = True,
        # TODO: No API yet for that
        #menus = menu_pending_movie(movie['IdPelicula'], wasSet = movie.get("Pending"),
        target = kodi_link(action='play_video', url=apiurl(movie['Fichero'])),
    )

def menu_pending_movie(movie_id, wasSet):
    label = _("Desmarcar pendiente") if wasSet else _('Marcar pendiente')
    action = 'unmark_pending_movie' if wasSet else 'mark_pending_movie'
    return [
        (label, kodi_action(
            action=action,
            movie_id=movie_id,
        )),
    ]

def menu_follow_serie(serie_id, wasSet):
    label = _('Abandonar serie') if wasSet else _('Seguir serie')
    action = 'unfollow_serie' if wasSet else 'follow_serie'
    return [
        (label, kodi_action(
            action=action,
            serie_id=serie_id,
        )),
    ]

def follow_serie(serie_id):
    with busy():
        status = api('Alertas/subscribeToSerie/', serie_id)
        kodi_refresh()

def unfollow_serie(serie_id):
    with busy():
        status = api('Alertas/unsubscribeToSerie/', serie_id)
        kodi_refresh()

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
    movie_list,
    play_video,
    pending_list,
    follow_serie,
    unfollow_serie,
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
