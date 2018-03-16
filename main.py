from xbmcswift2 import Plugin
import re
import requests
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import xbmcplugin
import base64
import random
import urllib
import sqlite3
import time,datetime
import threading
import json

import os,os.path

from struct import *
from collections import namedtuple


plugin = Plugin()
big_list_view = False



def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')

def log(v):
    xbmc.log(repr(v),xbmc.LOGERROR)


def get_icon_path(icon_name):
    if plugin.get_setting('user.icons') == "true":
        user_icon = "special://profile/addon_data/%s/icons/%s.png" % (addon_id(),icon_name)
        if xbmcvfs.exists(user_icon):
            return user_icon
    return "special://home/addons/%s/resources/img/%s.png" % (addon_id(),icon_name)

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def escape( str ):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def unescape( str ):
    str = str.replace("&lt;","<")
    str = str.replace("&gt;",">")
    str = str.replace("&quot;","\"")
    str = str.replace("&amp;","&")
    return str

def delete(path):
    dirs, files = xbmcvfs.listdir(path)
    for file in files:
        xbmcvfs.delete(path+file)
    for dir in dirs:
        delete(path + dir + '/')
    xbmcvfs.rmdir(path)



@plugin.route('/service')
def service():
    threading.Thread(target=dr).start()



def _handle_paging(result):
    items = result['Items']
    while 'Next' in result['Paging']:
        result = _http_request(result['Paging']['Next'])
        items.extend(result['Items'])
    return items

def _http_request(url):
    try:
        return json.loads(requests.get(url).content)
    except:
        pass


@plugin.route('/dr')
def dr():
    servicing = 'special://profile/addon_data/plugin.video.dr.strms/servicing'
    if xbmcvfs.exists(servicing):
        return
    f = xbmcvfs.File(servicing,'wb')
    #f.write('')
    f.close()
    folder = 'special://profile/addon_data/plugin.video.dr.strms/TV/'
    delete(folder)
    xbmcvfs.mkdirs(folder)
    for channel in ['dr-ultra','dr-ramasjang']:

        childrenFront = _http_request('http://www.dr.dk/mu-online/api/1.2/page/tv/children/front/%s' % channel)
        programs = _handle_paging(childrenFront['Programs'])
        #log(programs)
        for program in programs:
            #log((program['SeriesTitle'],program['PrimaryImageUri'],program['SeriesSlug']))
            title = program['SeriesTitle']
            #log((title,type(title)))
            seriesTitle = urllib.quote(title.encode("utf8"))
            dir = '%s%s/' % (folder,seriesTitle)
            xbmcvfs.mkdirs(dir)
            f = xbmcvfs.File(dir+'tvshow.nfo','wb')
            xml ='''
            <tvshow>
                   <title>%s</title>
                   <thumb aspect="banner">%s</thumb>
            </tvshow>
            ''' % (title,program['PrimaryImageUri'])
            f.write(xml.encode("utf8"))
            f.close()
            programEpisodes = _http_request('http://www.dr.dk/mu-online/api/1.2/list/%s' % program['SeriesSlug'])
            #log(programEpisodes)
            episodes = _handle_paging(programEpisodes)
            #log(episodes)
            i = 1
            for episode in episodes:
                #break
                log(episode)
                #log((program['Title'],program['Subtitle'],program['PrimaryImageUri'],program['Slug']))
                episodeDetails = _http_request('http://www.dr.dk/mu-online/api/1.2/programcard/%s' % program['Slug'])
                #log(episodeDetails)
                video = episodeDetails['PrimaryAsset']['Uri']
                log(video)
                streams = _http_request(video)
                uri = None
                for link in streams['Links']:
                    #log(link)
                    if link['Target'] == 'HLS':
                        uri = link['Uri']
                        break
                #log(uri)
                episodeTitle = "%s - %s" % (program['Title'],program.get('Subtitle',str(i)))
                i += 1
                f = xbmcvfs.File(dir+urllib.quote(episodeTitle.encode("utf8"))+'.nfo','wb')
                xml ='''
                <episodedetails>
                       <title>%s</title>
                       <thumb aspect="banner">%s</thumb>
                       <plot>%s</plot>
                </episodedetails>
                ''' % (episodeTitle,program['PrimaryImageUri'],episodeDetails.get('Description'))
                f.write(xml.encode("utf8"))
                f.close()
                f = xbmcvfs.File(dir+urllib.quote(episodeTitle.encode("utf8"))+'.strm','wb')
                f.write(uri.encode("utf8"))
                f.close()
            #return
            #break
    xbmcvfs.delete(servicing)
    #old_folder = 'special://profile/addon_data/plugin.video.dr.strms/TV.old/'
    #tv_folder = 'special://profile/addon_data/plugin.video.dr.strms/TV/'
    #xbmcvfs.rename(tv_folder,old_folder)
    #xbmcvfs.rename(new_folder,tv_folder)
    #delete(old_folder)

@plugin.route('/')
def index():
    items = []
    context_items = []

    items.append(
    {
        'label': "Make DR Ultra and Ramasjang strms in addon_data folder",
        'path': plugin.url_for('service'),
        'thumbnail':get_icon_path('settings'),
        'context_menu': context_items,
    })

    return items

if __name__ == '__main__':
    plugin.run()
