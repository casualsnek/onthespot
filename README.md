![Logo](src/onthespot/resources/icon.png)

# Onthespot

qt based music downloader written in python.

![Screenshot](https://i.imgur.com/C4V94gy.png)

### Discord for discussions: [Discord Invite](https://discord.gg/hz4mAwSujH)
If you have an idea for an improvement or feature, create a issue or join the discord server to discuss!

# 1. Installing/launching application:
## 1.1. Launch without installing - from source

Make sure [ffmpeg](https://ffmpeg.org/), [python3](https://www.python.org/downloads) and [Git](https://git-scm.com/downloads) are installed and available on your `$PATH`. If you are on windows, you also need to install the [Microsoft C++ build tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and restart your computer before starting the build process.
  1. Download or Clone the repo ```git clone https://github.com/casualsnek/onthespot```
  1. Navigate to the onthespot directory ```cd onthespot```
  1. Install the package ```pip install -r requirements.txt```
  1. Navigate to source directory ```cd src```
  1. Launch the application with ```python3 portable.py```

## 1.2. Launch with installing - from source

The requirements are the same as "Launching without installing" above.

1. Download or Clone the repo ```git clone https://github.com/casualsnek/onthespot```
1. Navigate to the onthespot directory ```cd onthespot```
1. Build the package ```python -m build```
1. Install the package ```pip install ./dist/*.whl```
1. Launch the application with ```onthespot_gui```

## 1.3. Using portable prebuilt binaries
### On Linux
#### Arch Linux
`onthespot` is available for arch linux and arch linux based distributions in arch user repository (aur) as [onthespot-git](https://aur.archlinux.org/packages/onthespot-git).

You can install `onthespot` using your favourite aur helper.

For eg: using yay
```
yay -Sy onthespot-git
```

#### Other Distributions
Download Latest 'onthespot_linux' from the release section and execute with
 ```
 chmod +x onthespot_linux
 ./onethespot_linux
 ```
### On Windows
Download Latest 'onthespot_win_ffm.exe' or 'onthespot_win.exe' from the Release section and execute by double-clicking the downloaded file.

The binaries with filename ending with '_ffm' have ffmpeg bundled and should not require manual installation.

If you are using binaries that does not bundle ffmpeg and downloads gets stuck at 99% with ```Converting``` on progress text, you are missing ffmpeg ! Please install it by following the instructions below

#### Installing ffmpeg in windows
- Open Windows Explorer and Navigate to ```C:\``` Drive and make a folder name ```ffmpeg``` there
- Download ffmpeg zip from [https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z) then copy the ``bin`` folder from zip to ```C:\ffmpeg```
- Open CMD as administrator and run the command: ```setx /m PATH "C:\ffmpeg\bin;%PATH%"```

Now the application should work as expected.

# 2. Building/packaging manually
Building or packaging on any OS requires Git, Python3 and Pip installed. Make sure you have them installed !

## 2.1. Building portable binaries
### 2.1.1 On Linux/nix
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

### 2.1.2. On Windows

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

### 2.1.3. On MacOS

**NOTE :** This only builds an app for the specific processor architecture you are on. It does not build a universal binary

Open terminal emulator and run the following command to clone the repository and build.
```bash
git clone https://github.com/casualsnek/onthespot
cd onthespot
```

If you want builds with ffmpeg embedded download ffmpeg binaries for your os from [Here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z).
Create a new directory named 'ffbin_mac' in repository root directory. Copy three files 'ffmpeg', 'ffprobe', 'ffplay' from the downloaded archive to the newly created 'ffbin_mac' directory then run:
```bash
./build_mac.sh
```
After the command completes, you should have a 'dist' directory in repository root containing the 'onthespot_mac.app' binary.

## 2.2.  Building wheel for installing with pip
You can also build onthespot as wheel and install it as python module via pip in your system. It provides better integration with system, like using your system's Qt style and themes as well as you can use provided icon and .desktop file for better integration under linux systems.

Make sure you have set up tools installed !

Open terminal emulator and run the following command to clone the repository and build.
```bash
git clone https://github.com/casualsnek/onthespot
cd onthespot
python -m build
```
This will create a dist directory containing .whl file that can now be installed with pip, the application can be launched with the command ```onthespot_gui``` or ```python3 -m onthespot``` after installing !

**NOTE :** If you are packaging onthespot for distribution, copy ```src/onthespot/resources/icon.svg``` to either ```/usr/share/icons/hicolor/scalable/apps/casual_onthespot.svg``` or ```$HOME/.local/share/icons/hicolor/scalable/apps/casual_onthespot.svg```, and ``` src/onthespot/resources/org.eu.casualsnek.onthespot.desktop``` to either ```/usr/share/applications/org.eu.casualsnek.onthespot.desktop``` or ```$HOME/.local/share/applications/org.eu.casualsnek.onthespot.desktop```. This allows application to be better integrated to desktop environments !

<br>
If you have ideas for improvement/features create an issue or join discord server for discussion !

# 3. Basic Usage
## Getting started
When launching the application for the first time, you will get a warning that no spotify accounts are added. Dismiss the warning, and add your account(s) at the bottom of the configuration tab. Having multiple accounts will let you download multiple songs at a time.

## Searching/Downloading via query
In the 'Search' tab, you can enter your query click `search` to search for songs/artists/albums/playlists.
You can then download media in the resulting list by clicking on the `download` button.
Optionally, you can bulk download by clicking on any of the buttons on the below the table.
*Note that Media Type other than 'Tracks' can take a little longer to parse and download. The application may appear to be frozen in this state !*

## Downloading by URL
Enter the url in the search field then click download.
You can also enter path of text file containing URL, and it will queue all url(s) in it !
*Note that Media Type other than 'Tracks' can take a little longer to parse and download. Application may appear to be frozen in this state !*

## Download status
The download status and progress can be viewed by navigating to the 'Progress' tab. 

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
  - artist : Name of artist of track
  - album : Name of album the track is in *
  - name : Name of track
  - rel_year : Release year of track
  - disc_number : Disk number in which track lies *
  - track_number : Serial Number of track in album *
  - playlist_name : Name of playlist if the track is being downloaded as part of playlist *
  - playlist_owner : Name of playlist if the track is being downloaded as part of playlist *
  - playlist_desc : Description of playlist if the track is being downloaded as part of playlist *
  - genre : Genre of song *
  - label : Name of record label
  - explicit : 'Explicit' if the song is marked explicit else it will be blank
  - trackcount : Total number of tracks on the album this track is in
  - disccount : Total number of discs on the album this track is in
  - spotid : Spotify ID
  - Example: ```Song: {name} of album: {album} Released in {rel_year}```.
  
The value of variables with their description ending in * maybe empty in some cases. This can also be a path.

- **Album directory name formatter**: 
This option allows you set the naming scheme of the directories for downloaded tracks. 
Variables can be used by enclosing them between `{}`. A few variables are available to use in the naming scheme:
  - artist : name of the main artist of the album
  - rel_year: the release year of the album *
  - album: name of the album
  - playlist_name : Name of playlist if the track is being downloaded as part of playlist *
  - playlist_owner : Name of playlist if the track is being downloaded as part of playlist *
  - playlist_desc : Description of playlist if the track is being downloaded as part of playlist *
  - genre : Genre of song *
  - label : Name of record label
  - Example: ```{artist}/{rel_year}/{album}```. 

The value of variables with their description ending in * maybe empty in some cases. This can be a path too.

- **Download chunk size**: 
Size of chunks (bytes) used for downloading.

- **Disable bulk download notice**: 
Enabling this will disable popup dialogs about status when using bulk downloads.

- **Recoverable downloads retry delay**: 
Time to wait before attempting another download after failed attempt.

- **Skip bytes at the end (download end skip bytes)**: 
Sometimes the last few bytes of a track can't be downloaded, leading to a 'PD Error' which causes the downloads to fail constantly.
This option sets the number of bytes to skip downloading when this happens.
The value might change but the current working value is '167' bytes. If you get 'decode errors' or incomplete song downloads, try setting it to 0.

- **Force Artist/Album dir for track/playlist items**: 
If this is disabled the tracks downloaded will be placed in the root of download directory instead of artist/album directories.
Enabling this might cause slower download parsing but makes organising music easier.

- **Media Format**: 
Format of media you want your final music download to be in. 
Do not include '.' in it. This setting will be ignored while using the raw media download option.

# 5. Issues
Decode error: If you are receiving this error, your account might have gotten restricted. Wait some time or try a different account. The application may crash frequently as there is no proper exception handling yet. You can help by opening a new issue with the error message displayed in your console window after the application misbehaves.
 
# 6. Contributing/Supporting
You can write code to include additional feature or bug fixes or make a issue regarding bugs and features or just spread the work about the application :)
If you want to support financially, you can visit [Here](https://github.com/casualsnek/casualsnek) and support through open collective or BTC
If you like the project, show your support by giving it a star :) !
