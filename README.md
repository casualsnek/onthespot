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
If your download(s) is stuck at 99% and displays "Converting" for the progress text, you are missing [ffmpeg](https://ffmpeg.org/download.html), download from the "Get packages & executable files" section.



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

# TODOS
 - Synced lyrics downloads
 - Improve UI/UX ( Suggestions needed by users )
 - Refactor code
 
# Contributing/Supporting
You can write code to include additional feature or bug fixes or make a issue regarding bugs and features or just spread the work about the application :)
If you want to support financially, you can visit [Here](https://github.com/casualsnek/casualsnek) and support through open collective orBTC

If you like the project, show your support by giving it a star :) !
