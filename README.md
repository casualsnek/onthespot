# Onthespot
qt based music downloader written in python.
![Screenshot](https://i.imgur.com/C4V94gy.png)

### Discord for discussions: [Discord Invite](https://discord.gg/2t6BNVgZ)
If you have an idea for an improvement or feature, create a issue or join the discord server to discuss!

# Installing/launching application from source:
Make sure [python3](https://www.python.org/downloads) and [Git](https://git-scm.com/downloads) are installed on your system then
  - Download or Clone the repo ```git clone https://github.com/casualsnek/onethespot```
  - Navigate to the onthespot directory ```cd onethespot```
  - Install the dependencies with ```pip install -r requirements.txt```
  - Launch the application with ```python3 onthespot.py```
  

  Or you can 
  
## Launch using prebuilt binaries
### On Linux
Download the latest 'onthespot_linux' binary from the [release](https://github.com/casualsnek/onethespot/releases) section and execute with
 ```chmod +x onthespot_linux && ./onethespot_linux```
 
### On Windows (binaries not built yet 04/10/22)
Download the latest 'onthespot_win.exe' binary from the [release](https://github.com/casualsnek/onethespot/releases) section and execute it by double clicking the downloaded file.
If your download(s) is stuck at 99% and displays "Converting" for the progress text, you are missing [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z), download the 7z then extract it using an archive software. Open the ffmpeg folder, go into bin then drag all 3 exe's into C:\Windows and restart the onethestop application.



# Usage
### Getting started
On your first launch of application you will get a warning that no spotify accounts are added, click ok and add your account(s) at the bottom of the application. After adding your accounts, close and restart the application.
Having multiple accounts will let you download multiple songs at a time.

### Searching/Downloading via query
Click on 'Search' tab then enter your query and cick search to search for songs/artists/albums/playlists and click download.

### Downloading by URL
Enter the url in the url field then click download.

### Checking the download status
The download status and progress can be viewed by navigating to 'Progress' tab.
Note that Media Type other than 'Tracks' can take a little longer to parse and download. The application may appear to be frozen in this state but it isn't anything to worry about.

# Configuration
### General Configuration options
- Max download workers   : It is the number of threads to be used for media downloads. Set this to the number of accounts you added. Changing this setting requires an application restart to take effect.
 - Parsing Account SN     : It is the number shown at left side of the username in the accounts table. The number is the account responsible for providing search results and parsing download url(s).
 - Download Location      : The root folder where downloaded media are placed in.
 - Download delay         : Time in seconds to wait before next download after a successful download.
 - Max retries            : Number of times to retry a download before moving on.
 - Max search results     : The number of items to show in search result for each type of media. Example: setting it to '1' shows one result for artist, album, track and playlist resulting in 4 total search results.
 - Raw media download     : Downloads files (they will be .ogg) to disk without converting to set media format, it also disables metadata writing and thumbnail embedding.
 - Force premium          : Use this if your premium accounts shows FREE in accounts table, this applies to all added accounts so it's not recommeded to use with a combination of free and premium accounts. Don't use if account isn't premium.
 - Show/Hide Advanced Configuration: Enable/Disables the Advanced configuration tab.
 - Save setting           : Saves the current setting and applies it to the application.

### Advanced Configuration
Default track names are  ```AlbumFormatter/TrackName```

- Track name formatter:
This option allows you to set the naming scheme of downloaded tracks.
Variables can be used by enclosing them between `{}`. A few variables are available to use in the naming scheme:
  - artist : name of artist of track
  - album : name of album the track is in *
  - name : name of track
  - rel_year : release year of track
  - disc_number : disk number in which track lies *
  - track_number : serial Number of track in album *
  - spotid : Spotify ID
  - Example: ```Song: {name} of album: {album} Released in {rel_year}```.
The value of variables with their description ending in * maybe empty in some cases.
This can be a path.

- Album directory name formatter:
This option allows you set the naming scheme of the directories for downloaded tracks. 
Variables can be used by enclosing them between `{}`. A few variables are available to use in the naming scheme:
  - artist : name of the main artist of the album
  - rel_year: the release year of the album *
  - album: name of the album
  - Example: ```{artist}/{rel_year}/{album}```. 
  - The value of variables with their description ending in * maybe empty in some cases. This can be a path too.

- Download chunk size:
Size of chunks (bytes) used for downloading.

- Disable bulk download notice:
Enabling this will disable popup dialog about status when using buld download buttons below the search results

- Recoverable downloads retry delay:
Time to wait before attempting another download.

- Skip bytes at the end (download end skip bytes) 
Sometimes the last few bytes of a track can't be downloaded which causes 'PD Error' to show up which causes downloads to fail constantly, this sets the number of bytes to skip downloading if this happens.
The value might change but the current working vaue is '167' bytes. If you get 'decode errors' or incomplete song downloads try setting it to 0.

- Force Artist/Album dir for track/playlist items
If this is disabled the tracks downloaded will be placed in the root of download directory instead of artist/album directories.
Enabling this might cause slower download parsing but makes orgainsing music easier.

- Media Format
Format of media you want your final music download to be in. 
Do not include '.' in it. This setting will be ignored while using the raw media download option.

# Issues
Decode error: If you are receiving this error, your account might have got restricted. Wait some time or try a different account.
The application may crash frequently as there is no proper exception handling yet. You can help by opening a new issue with the error message displayed in your console window after the application misbehaves.

# Running using binaries
## On Linux
Download Latest 'onthespot_linux' from the release section and execute with:

  
# Running using binaries
## On Linux
Download Latest 'onthespot_linux' from the release section and execute with
 ```
 chmod +x onthespot_linux
 ./onethespot_linux
 ```
 ## On Windows
Download Latest 'onthespot_win.exe' from the release section and execute by double clicking the downloaded file
If your downloads gets stuck at 99% and ```Converting``` on progress text, you are missing ffmpeg ! Please install it by following the instructions below

### Installing ffmpeg in windows
- Open Windows Explorer and Navigate to ```C:\`` Drive and make a folder name ```ffmpeg``` there
- Download ffmpef zip from [https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) then copy the ``bin`` folder from zip to ```C:\ffmpeg```
- Open CMD as administrator and run the command: ```setx /m PATH "C:\ffmpeg\bin;%PATH%"```

Now the application should work as expected.

If you have ideas for improvement/features create a issue or join discord server for discussion !

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
 
# Contributing/Supporting
You can write code to include additional feature or bug fixes or make a issue regarding bugs and features or just spread the work about the application :)

If you want to support financially, you can visit [Here](https://github.com/casualsnek/casualsnek) and support through open collective orBTC

If you like the project, show your support by giving it a star :) !
