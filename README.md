# Onthespot
qt based music downloader written in python.
![Screenshot](https://i.imgur.com/C4V94gy.png)

### Discord for discussions: [Discord Invite](https://discord.gg/2t6BNVgZ)
If you have an idea for an improvement or feature, create a issue or join the discord server to discuss!

# 1. Installing/launching application without building the binary:
## 1.1. From source
Make sure [Python3](https://www.python.org/downloads) and [Git](https://git-scm.com/downloads) are installed on your system.
  - Download or Clone the repo ```git clone https://github.com/casualsnek/onthespot```
  - Navigate to the onthespot directory ```cd onthespot```
  - Install the dependencies with ```pip install -r requirements.txt```
  - (ONLY IF USING WINDOWS) Install another dependancy with ```pip install winsdk```
  - Launch the application with ```python3 onthespot.py```
 
 
## 1.2. Using prebuilt binaries
### On Linux
Download the latest 'onthespot_linux' from the [releases](https://github.com/casualsnek/onthespot/releases) and execute with
 ```chmod +x onthespot_linux && ./onethespot_linux```

### On Windows
Download the latest 'onthespot_win_ffm.exe' or 'onthespot_win.exe' from the [releases](https://github.com/casualsnek/onthespot/releases) and execute by double clicking the downloaded file.

The binaries with filename ending with '_ffm' have ffmpeg bundled.

If you are using binaries that doesn't bundle ffmpeg, please install it by following the instructions below

### Installing ffmpeg in windows
- Open Windows Explorer and navigate to your ```C:\``` drive and make a folder named ```ffmpeg```.
- Download the ffmpeg zip from [https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) then copy the ``bin`` folder from zip to ```C:\ffmpeg```
- Open cmd as an administrator and run the command: ```setx /m PATH "C:\ffmpeg\bin;%PATH%"```

Restart the application and it should work as expected.


## 1.3. Building manually
Building on any OS requires [Git](https://git-scm.com/downloads), [Python3](https://www.python.org/downloads) and Pip (included with python) installed. 

### 1.3.1. On Linux
Open terminal emulator and run the following command to clone the repository and build.
```bash && git clone https://github.com/casualsnek/onthespot && cd onthespot```

If you want builds with ffmpeg bundled, download the [ffmpeg binaries](https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz), run ```tar xvf ffmpeg-git-amd64-static.tar.xz``` where it is downloaded to extract the files and you'll get a folder named "ffmpeg-git-*timestamp*-amd64-static", open this directory and copy 'ffmpeg' and 'ffprobe'. Create a new directory named 'ffbin_nix' in the repository root directory. Paste the 2 files you've just copied here

To build run
```bash
bash ./build_linux.sh
```
After the command completes, you should have a 'dist' directory in the repository root folder containing the built 'onthespot_linux' binary.

### 1.3.2. On Windows
Download the [Microsoft C++ build tools](https://visualstudio.microsoft.com/visual-cpp-build-tools) and [Git](https://git-scm.com/downloads). Install both and reboot your computer. (Microsoft C++ Build Tools required for building the simpleaudio python module)

Open cmd and run ```git clone https://github.com/casualsnek/onthespot && cd onthespot```

If you want builds with ffmpeg bundled download the [ffmpeg binaries](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z), extract, go into the bin folder and copy 'ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe'. Create a new directory named 'ffbin_win' in repository root directory. Copy the three files here.

To build run ```build_winC1.bat && build_winC2.bat```.
After the command completes, you should have a 'dist' directory in repository root containing built 'onthespot_win.exe' binary.

# 2. Basic Usage
### Getting started
On your first launch of application you will get a warning that no spotify accounts are added, click ok and add your account(s) at the bottom of the application. After adding your accounts, close and restart the application. Having multiple accounts will let you download multiple songs at a time.

### Searching/Downloading via query
Click on 'Search' tab, enter your query and cick search. You can search songs, artists, albums or playlists. Click download to download.
You can download any media like 'Albums', 'Tracks', etc., that appear in the results all at once by using the download buttons below the results table.
*Note that Media Type other than 'Tracks' can take a little longer to parse and download. The application may appear to be frozen in this state while parsing*

### Downloading by URL
Enter the url in the url field then click download.
*Note that Media Type other than 'Tracks' can take a little longer to parse and download. The application may appear to be frozen in this state while parsing*

### Download status
The download status and progress can be viewed by navigating to the 'Progress' tab. 

# 3. Configuration
### 3.1. General Configuration options
- **Max download workers**   : It is the number of threads to be used for media downloads. Set this to the number of accounts you added. Changing this setting requires an application restart to take effect.
- **Parsing Account SN**              : It is the number shown at left side of the username in the accounts table. The number is the account responsible for providing search results and parsing download url(s).
- **Download Location**               : The root folder where downloaded media are placed in.
- **Download delay**                  : Time in seconds to wait before next download after a successful download.
- **Max retries**                     : Number of times to retry a download before moving on.
- **Max search results**              : The number of items to show in search result for each type of media. Example: setting it to '1' shows one result for artist, album, track and playlist resulting in 4 total search results.
- **Raw media download**              : Downloads files (they will be .ogg) to disk without converting to set media format, it also disables metadata writing and thumbnail embedding.
- **Force premium**                   : Use this if your premium accounts shows FREE in accounts table, this applies to all added accounts so it's not recommeded to use with a combination of free and premium accounts. Don't use if account isn't premium.
- **Enable desktop app play to download** : Enabling will automatically download songs you play on spotify desktop application. (Supported: Linux/Windows)
- **Show/Hide Advanced Configuration**: Enable/Disables the Advanced configuration tab.
- **Save setting**: Saves/Applies the settings

### 3.2. Advanced Configuration
Default track names are  ```AlbumFormatter/TrackName```

- **Track name formatter**: 
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
  The value of variables with their description ending in * maybe empty in some cases. This can also be a path.

- **Album directory name formatter**: 
This option allows you set the naming scheme of the directories for downloaded tracks. 
Variables can be used by enclosing them between `{}`. A few variables are available to use in the naming scheme:
  - artist : name of the main artist of the album
  - rel_year: the release year of the album *
  - album: name of the album
  - Example: ```{artist}/{rel_year}/{album}```. 
The value of variables with their description ending in * maybe empty in some cases. This can be a path too.

- **Download chunk size**: 
Size of chunks (bytes) used for downloading.

- **Disable bulk download notice**: 
Enabling this will disable popup dialog about status when using buld download buttons below the search results

- **Recoverable downloads retry delay**: 
Time to wait before attempting another download after failed attempt.

- **Skip bytes at the end (download end skip bytes)**: 
Sometimes the last few bytes of a track can't be downloaded which causes 'PD Error' to show up which causes downloads to fail constantly, this sets the number of bytes to skip downloading if this happens.
The value might change but the current working vaue is '167' bytes. If you get 'decode errors' or incomplete song downloads try setting it to 0.

- **Force Artist/Album dir for track/playlist items**: 
If this is disabled the tracks downloaded will be placed in the root of download directory instead of artist/album directories.
Enabling this might cause slower download parsing but makes orgainsing music easier.

- **Media Format**: 
Format of media you want your final music download to be in. 
Do not include '.' in it. This setting will be ignored while using the raw media download option.

# 4. Issues
Decode error: If you are receiving this error, your account might have got restricted. Wait some time or try a different account. The application may crash frequently as there is no proper exception handling yet. You can help by opening a new issue with the error message displayed in your console window after the application misbehaves.

# 5. TODOS
 - Synced lyrics downloads
 - Improve UI/UX ( Suggestions needed by users )
 - Refactor code
 
# 6. Contributing/Supporting
You can write code for features and/or bug fixes, you can make a issue or just spread the word about this application :)
If you want to support financially, you can visit [Here](https://github.com/casualsnek/casualsnek) and support through open collective or BTC.
If you like the project, show your support by giving it a star :) !
