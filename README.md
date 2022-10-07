# Onthespot
qt based music downloader written in python.
![Screenshot](https://i.imgur.com/C4V94gy.png)

### Discord for discussions: [Discord Invite](https://discord.gg/2t6BNVgZ)
If you have an idea for an improvement or feature, create a issue or join the discord server to discuss!

# 1. Installing/launching application:
## 1.1. From source
Make sure [python3](https://www.python.org/downloads) and [Git](https://git-scm.com/downloads) are installed on your system, if you are on windows you also need to install Microsoft C++ build tools from [HERE](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and restart your computer before starting build process.
  - Download or Clone the repo ```git clone https://github.com/casualsnek/onthespot```
  - Navigate to the onthespot directory ```cd onthespot```
  - Install the dependencies with ```pip install -r requirements.txt```
  - Launch the application with ```python3 onthespot.py```
 
 *Windows users should also follow these extra steps before running:* ```python3 onthespot.py```
 ```
 pip install winsdk
 ```
  
## 1.2. Using prebuilt binaries
### On Linux
Download Latest 'onthespot_linux' from the release section and execute with
 ```
 chmod +x onthespot_linux
 ./onethespot_linux
 ```
### On Windows
Download Latest 'onthespot_win_ffm.exe' or 'onthespot_win.exe' from the Release section and execute by double clicking the downloaded file.

The binaries with filename ending with '_ffm' have ffmpeg bundled and should not require manual installation.

If you are using binaries that does not bundle ffmpeg and downloads gets stuck at 99% with ```Converting``` on progress text, you are missing ffmpeg ! Please install it by following the instructions below

#### Installing ffmpeg in windows
- Open Windows Explorer and Navigate to ```C:\``` Drive and make a folder name ```ffmpeg``` there
- Download ffmpef zip from [https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) then copy the ``bin`` folder from zip to ```C:\ffmpeg```
- Open CMD as administrator and run the command: ```setx /m PATH "C:\ffmpeg\bin;%PATH%"```

Now the application should work as expected.


# 2. Building manually
Building on any OS requires Git, Python3 and Pip installed. Make sure you have them installed !

## 2.1. On Linux/nix
Open terminal emulator and run the following command to clone the repository and build.
```bash
git clone https://github.com/casualsnek/onthespot
cd onthespot
```
If you want builds with ffmpeg embedded download ffmpeg binaries for your os from [Here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z). 
Create a new directory named 'ffbin_nix' in repository root directory. Copy three files 'ffmpeg', 'ffprobe', 'ffplay' from downloaded archive to just created 'ffbin_nix' directory then run;
```bash
bash ./build_linux.sh
```
After the command completes, you should have a 'dist' directory in repository root containing built 'onthespot_linux' binary.

## 2.2. On Windows
Download Microsoft C++ build tools from [Here](https://visualstudio.microsoft.com/visual-cpp-build-tools/). Setup/Install it and reboot your computer. ( Required for building simpleaudio  python module)

Open cmd and run the following command to clone the repository and build.
```cmd
git clone https://github.com/casualsnek/onthespot
cd onthespot
```
If you do not have git installed you can also download the Project source zip from github, extract it and open cmd on repository root.
If you want builds with ffmpeg embedded download ffmpeg binaries for your os from [Here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z). 
Create a new directory named 'ffbin_win' in repository root directory. Copy three files 'ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe' from downloaded archive to just created 'ffbin_win' directory then run;
```cmd
build_winC1.bat
build_winC2.bat
```
After the command completes, you should have a 'dist' directory in repository root containing built 'onthespot_win.exe' binary.


If you have ideas for improvement/features create a issue or join discord server for discussion !

# 3. Basic Usage
## Getting started
On your first launch of application you will get a warning that no spotify accounts are added, click ok and add your account(s) at the bottom of the application. After adding your accounts, close and restart the application. Having multiple accounts will let you download multiple songs at a time.

## Searching/Downloading via query
Click on 'Search' tab then enter your query and cick search to search for songs/artists/albums/playlists and click download.
You can download any media like 'Albums', 'Tracks', etc., that appear on the results table all at once by using the download buttons below the results table.
*Note that Media Type other than 'Tracks' can take a little longer to parse and download. The application may appear to be frozen in this state !*

## Downloading by URL
Enter the url in the url field then click download.
*Note that Media Type other than 'Tracks' can take a little longer to parse and download. Application may appear to be frozen in this state !*

## Download status
The download status and progress can be viewed by navigating to 'Progress' tab. 

# 4. Configuration
### 4.1. General Configuration options
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

### 4.2. Advanced Configuration
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

# 5. Issues
Decode error: If you are receiving this error, your account might have got restricted. Wait some time or try a different account. The application may crash frequently as there is no proper exception handling yet. You can help by opening a new issue with the error message displayed in your console window after the application misbehaves.

# 6. TODOS
 - Synced lyrics downloads
 - Improve UI/UX ( Suggestions needed by users )
 - Refactor code
 
# 7. Contributing/Supporting
You can write code to include additional feature or bug fixes or make a issue regarding bugs and features or just spread the work about the application :)
If you want to support financially, you can visit [Here](https://github.com/casualsnek/casualsnek) and support through open collective or BTC
If you like the project, show your support by giving it a star :) !
