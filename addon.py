import os
import sys
import urllib
import urlparse

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

# Make sure library folder is on the path
addon = xbmcaddon.Addon("plugin.audio.subsonic")
sys.path.append(xbmc.translatePath(os.path.join(
    addon.getAddonInfo("path"), "lib")))

import libsonic_extra


class Plugin(object):
    """
    Plugin container
    """

    def __init__(self, addon_url, addon_handle, addon_args):
        self.addon_url = addon_url
        self.addon_handle = addon_handle
        self.addon_args = addon_args

        # Retrieve plugin settings
        self.url = addon.getSetting("subsonic_url")
        self.username = addon.getSetting("username")
        self.password = addon.getSetting("password")

        self.random_count = addon.getSetting("random_count")
        self.bitrate = addon.getSetting("bitrate")
        self.trans_format = addon.getSetting("trans_format")

        # Create connection
        self.connection = libsonic_extra.Connection(
            self.url, self.username, self.password)

    def build_url(self, query):
        """
        """

        parts = list(urlparse.urlparse(self.addon_url))
        parts[4] = urllib.urlencode(query)

        return urlparse.urlunparse(parts)

    def walk_genres(self):
        """
        Request Subsonic's genres list and iterate each item.
        """

        response = self.connection.getGenres()

        for genre in response["genres"]["genre"]:
            yield genre

    def walk_artists(self):
        """
        Request SubSonic's index and iterate each item.
        """

        response = self.connection.getArtists()

        for index in response["artists"]["index"]:
            for artist in index["artist"]:
                yield artist

    def walk_album_list2_genre(self, genre):
        """
        """

        offset = 0

        while True:
            response = self.connection.getAlbumList2(
                ltype="byGenre", genre=genre, size=500, offset=offset)

            if not response["albumList2"]["album"]:
                break

            for album in response["albumList2"]["album"]:
                yield album

            offset += 500

    def walk_album(self, album_id):
        """
        Request Album and iterate each song.
        """

        response = self.connection.getAlbum(album_id)

        for song in response["album"]["song"]:
            yield song

    def walk_playlists(self):
        """
        Request SubSonic's playlists and iterate over each item.
        """

        response = self.connection.getPlaylists()

        for child in response["playlists"]["playlist"]:
            yield child

    def walk_playlist(self, playlist_id):
        """
        Request SubSonic's playlist items and iterate over each item.
        """

        response = self.connection.getPlaylist(playlist_id)

        for order, child in enumerate(response["playlist"]["entry"], start=1):
            child["order"] = order
            yield child

    def walk_directory(self, directory_id):
        """
        Request a SubSonic music directory and iterate over each item.
        """

        response = self.connection.getMusicDirectory(directory_id)

        for child in response["directory"]["child"]:
            if child.get("isDir"):
                for child in self.walk_directory(child["id"]):
                    yield child
            else:
                yield child

    def walk_artist(self, artist_id):
        """
        Request a SubSonic artist and iterate over each album.
        """

        response = self.connection.getArtist(artist_id)

        for child in response["artist"]["album"]:
            yield child

    def walk_random_songs(self, size, genre=None, from_year=None,
                          to_year=None):
        """
        """

        response = self.connection.getRandomSongs(
            size=size, genre=genre, fromYear=from_year, toYear=to_year)

        for song in response["randomSongs"]["song"]:
            song["id"] = int(song["id"])

            yield song

    def route(self):
        mode = self.addon_args.get("mode", ["main_page"])[0]
        getattr(self, mode)()

    def add_track(self, track, show_artist=False):
        """
        """

        cover_art_url = self.connection.getCoverArtUrl(track["id"])
        url = self.connection.streamUrl(
            sid=track["id"], maxBitRate=self.bitrate,
            tformat=self.trans_format)

        if show_artist:
            li = xbmcgui.ListItem(track["artist"] + " - " + track["title"])
        else:
            li = xbmcgui.ListItem(track["title"])

        li.setIconImage(cover_art_url)
        li.setThumbnailImage(cover_art_url)
        li.setProperty("fanart_image", cover_art_url)
        li.setProperty("IsPlayable", "true")
        li.setInfo(type="Music", infoLabels={
            "Artist": track["artist"],
            "Title": track["title"],
            "Year": track.get("year"),
            "Duration": track.get("duration"),
            "Genre": track.get("genre")})

        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle, url=url, listitem=li)

    def add_album(self, album, show_artist=False):
        cover_art_url = self.connection.getCoverArtUrl(album["id"])
        url = self.build_url({
            "mode": "track_list",
            "album_id": album["id"]})

        if show_artist:
            li = xbmcgui.ListItem(album["artist"] + " - " + album["name"])
        else:
            li = xbmcgui.ListItem(album["name"])

        li.setIconImage(cover_art_url)
        li.setThumbnailImage(cover_art_url)
        li.setProperty("fanart_image", cover_art_url)

        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle, url=url, listitem=li, isFolder=True)

    def main_page(self):
        """
        Display main menu.
        """

        menu = [
            {"mode": "playlists_list", "foldername": "Playlists"},
            {"mode": "artist_list", "foldername": "Artists"},
            {"mode": "genre_list", "foldername": "Genres"},
            {"mode": "random_list", "foldername": "Random songs"}]

        for entry in menu:
            url = self.build_url(entry)

            li = xbmcgui.ListItem(entry["foldername"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def playlists_list(self):
        """
        Display playlists.
        """

        for playlist in self.walk_playlists():
            cover_art_url = self.connection.getCoverArtUrl(
                playlist["coverArt"])
            url = self.build_url({
                "mode": "playlist_list", "playlist_id": playlist["id"]})

            li = xbmcgui.ListItem(playlist["name"], iconImage=cover_art_url)
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def playlist_list(self):
        """
        Display playlist tracks.
        """

        playlist_id = self.addon_args["playlist_id"][0]

        for track in self.walk_playlist(playlist_id):
            self.add_track(track, show_artist=True)

        xbmcplugin.setContent(self.addon_handle, "songs")
        xbmcplugin.endOfDirectory(self.addon_handle)

    def genre_list(self):
        """
        Display list of genres menu.
        """

        for genre in self.walk_genres():
            url = self.build_url({
                "mode": "albums_by_genre_list",
                "foldername": genre["value"].encode("utf-8")})

            li = xbmcgui.ListItem(genre["value"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def albums_by_genre_list(self):
        """
        Display album list by genre menu.
        """

        genre = self.addon_args["foldername"][0].decode("utf-8")

        for album in self.walk_album_list2_genre(genre):
            self.add_album(album, show_artist=True)

        xbmcplugin.setContent(self.addon_handle, "albums")
        xbmcplugin.endOfDirectory(self.addon_handle)

    def artist_list(self):
        """
        Display artist list
        """

        for artist in self.walk_artists():
            cover_art_url = self.connection.getCoverArtUrl(artist["id"])
            url = self.build_url({
                "mode": "album_list",
                "artist_id": artist["id"]})

            li = xbmcgui.ListItem(artist["name"])
            li.setIconImage(cover_art_url)
            li.setThumbnailImage(cover_art_url)
            li.setProperty("fanart_image", cover_art_url)
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.setContent(self.addon_handle, "artists")
        xbmcplugin.endOfDirectory(self.addon_handle)

    def album_list(self):
        """
        Display list of albums for certain artist.
        """

        artist_id = self.addon_args["artist_id"][0]

        for album in self.walk_artist(artist_id):
            self.add_album(album)

        xbmcplugin.setContent(self.addon_handle, "albums")
        xbmcplugin.endOfDirectory(self.addon_handle)

    def track_list(self):
        """
        Display track list.
        """

        album_id = self.addon_args["album_id"][0]

        for track in self.walk_album(album_id):
            self.add_track(track)

        xbmcplugin.setContent(self.addon_handle, "songs")
        xbmcplugin.endOfDirectory(self.addon_handle)

    def random_list(self):
        """
        Display random options.
        """

        menu = [
            {"mode": "random_by_genre_list", "foldername": "By genre"},
            {"mode": "random_by_year_list", "foldername": "By year"}]

        for entry in menu:
            url = self.build_url(entry)

            li = xbmcgui.ListItem(entry["foldername"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def random_by_genre_list(self):
        """
        Display random genre list.
        """

        for genre in self.walk_genres():
            url = self.build_url({
                "mode": "random_by_genre_track_list",
                "foldername": genre["value"].encode("utf-8")})

            li = xbmcgui.ListItem(genre["value"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def random_by_genre_track_list(self):
        """
        Display random tracks by genre
        """

        genre = self.addon_args["foldername"][0].decode("utf-8")

        for track in self.walk_random_songs(
                size=self.random_count, genre=genre):
            self.add_track(track, show_artist=True)

        xbmcplugin.setContent(self.addon_handle, "songs")
        xbmcplugin.endOfDirectory(self.addon_handle)

    def random_by_year_list(self):
        """
        Display random tracks by year.
        """

        from_year = xbmcgui.Dialog().input(
            "From year", type=xbmcgui.INPUT_NUMERIC)
        to_year = xbmcgui.Dialog().input(
            "To year", type=xbmcgui.INPUT_NUMERIC)

        for track in self.walk_random_songs(
                size=self.random_count, from_year=from_year, to_year=to_year):
            self.add_track(track, show_artist=True)

        xbmcplugin.setContent(self.addon_handle, "songs")
        xbmcplugin.endOfDirectory(self.addon_handle)


def main():
    """
    Entry point for this plugin.
    """

    addon_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    addon_args = urlparse.parse_qs(sys.argv[2][1:])

    # Route request to action
    Plugin(addon_url, addon_handle, addon_args).route()

# Start plugin from Kodi
if __name__ == "__main__":
    main()
