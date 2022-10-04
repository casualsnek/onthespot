# onthespot
![Screenshot](https://i.imgur.com/C4V94gy.png)

qt based music downloader written in python

### Just created this discord for discussions: [Discord Invite](https://discord.gg/2t6BNVgZ)

# Installing and launching application
Make sure python3 is installed on your system then:
  - Clone or download and extract the repository file: ```git clone https://github.com/casualsnek/onethespot```
  - Navigate to the onthespot directory ```cd onethespot```
  - Install the dependencies with ```pip install -r requirements.txt```
  - Launch the application with ```python3 onthespot.py```

Binary releases for windows will be worked on soon :). Note that this is in early stage of development, and some features are yet to be added. If you have ideas for improvement/features, create an issue for discussion !

# Getting started
On first launch, you might get a warning that no accounts have been added and the threads are not started.
You can add your accounts by using the login form at the bottom of the 'Configuration' tab. You can add multiple accounts to be able to download multiple songs at a time without getting limited but might slow down application startups
After adding accounts, close and restart the application and you should be good to go !

## Searching/Downloading
Click on 'OnTheSpot Search' tab then enter your search query and click search to search for songs/artists/albums/playlists using Spotify.
You can then start downloading by clicking on the 'Download' button on the row of your search result.
Note that Media Type other than 'Tracks' can take a little longer to parse and download. Application may appear to be frozen in this state but it is nothing to worry about !
You can bulk download any media like 'Albums', 'Tracks', etc., that appear on the results table by clicking the download button below the results table.

## Downloading by URL
Just enter the URL in the URL field then click download button, download should start.
Note that Media Type other than 'Tracks' can take a little longer to parse and download. Application may appear to be frozen in this state, but it is nothing to worry about !

## Download status
Download status/progress can be viewed by navigating to 'Progress tabs'

# General Configuration options
 - Max download workers   : It is the number of downloaders available for parallel media downloads. It is recommended you set it to the number of accounts you have added to the application. Changing this setting required application restart to take effect.
 - Parsing Account SN     : It is the Number shown at left side of username in Accounts table. The username corresponding to the SN is responsible for providing search results and parsing download URL(s).
 - Download Location      : The root folder where downloaded medias are saved. Click the browse button next to it to set a new location to download files in.
 - Download delay         : Time in seconds to wait before next download after successful download.
 - Max retries            : Number of download retries to perform before giving up the download process.
 - Max search results     : The number of items to show in search result for each type of media. Example: Setting it to '1' shows one result for Artist, Album, Track and Playlist resulting in 4 total search results.
 - Raw media download     : Downloads files (ogg) directly writes to disk without converting to set media format, it also disables metadata writing and thumbnail embedding.
 - Force premium          : Use this if your premium accounts shows FREE in accounts table, this applies to all added accounts so it's not recommended to use with a combination of free and premium accounts.
 - Show/Hide Advanced Configuration: Enable/Disables the Advanced configuration tab
 - Save setting           : Saves the current setting and applies it to the application.

# Advanced Configuration
Note: Track name and album directory names are set up in this path format  ```Album Formatter/Track Name```

### 1. Track name formatter:
This option allows you to set naming scheme of downloaded tracks. It can also be set as a path by using path separator in the name
Variables can be used by enclosing them between ```{}``` . Few variables are available to set the naming scheme of tracks:
  - artist : Name of artist of track.
  - album : Name of album the track is in. *
  - name : Name of track.
  - rel_year : Release year of track.
  - disc_number : Disk number in which track lies. *
  - track_number : Serial Number of track in album. *
  - spotid : ID of track as it is in Spotify.
Example: ```Song: {name} of album: {album} Released in {rel_year}```
The value of variables with their description ending in * may be empty in some cases.

### 2. Album directory name formatter
This option allows you to set naming scheme of directory in which the tracks are downloaded and organized. This can be a path as well.
Variables can be used by enclosing them between ```{}``` . Few variables are available to set the naming scheme of tracks:
 - artist : Name of main artist of album
 - rel_year: The release year of album. *
 - album: Name of the album

Example: ```{artist}/{rel_year}/{album}``` downloads the track on folder with artist's name containing directory Release year then in the Album name directory
The value of variables with their description ending in * may be empty in some cases.

### 3. Download chunk size:
Size of chunks in bytes of downloaded tracks.

### 4. Disable bulk download notice
Enabling this will disable popup dialog about status when using build download buttons below the search results

### 5. Recoverable downloads retry delay
Time to wait before retrying in case download fails due to Recoverable issues like network errors

### 6. Download end skip (Bytes)
Sometimes, the last few bytes cannot be downloaded, which causes 'PD Error' to show up and causes downloads to fail constantly. This sets up the number of bytes to skip downloading if this happens.
The value might change but the current working value is '167' bytes. If you get 'Decode errors' or Incomplete song downloads, try setting it to 0.

### 7. Force Artist/Album Dir for track/playlist items
If this is disabled, the tracks downloaded from playlist/individual track URL or search results get placed in root of download directory instead of artist/album directories.
Enabling this might cause slower download parsing but makes organizing music easier

### 8. Media Format
Format of media you want your final music download to be in. ( Do not include '.' in it !). This setting gets ignored while using raw media download option.

# Issues
Decode error : If you are getting into this error, your account might be restricted. Wait a little while or try a different account.
The application may crash frequently as there is no proper exception handling yet. You can help by opening a new issue with the error message displayed on your console window after the application misbehaves.
The readme also needs to be written properly.

# TODOS
 - Synced lyrics downloads
 - Improve UI/UX ( Suggestions needed by users )
 - Refactor code
 - ....
 
# Contributing/Supporting
You can write code to include additional feature or bug fixes or make a issue regarding bugs and features or just spread the work about the application :)
If you want to support financially, you can visit [Here](https://github.com/casualsnek/casualsnek) and support through open collective or BTC

If you like the project, show your support by giving it a star :) !


