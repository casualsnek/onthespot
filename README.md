# onethespot
qt based Spotify downloader written in python

# Basic usage
Make sure python3 is installed on your system
  - Clone or download and extract the repository file: ```git clone https://github.com/casualsnek/onthespot```
  - Navigate to the onthespot directory ```cd onthesport```
  - Install the dependencies with ```pip install -r requirements.txt```
  - Launch the application with ```python3 onthespot.py```

# Configuring
Accounts can be added from the main page of application, it is recommended to use multiple free accounts and set the max number of workers to number of accounts added. Only username/email and password based login is available right now !
You need to restart application after adding accounts or changing thread settings.

# Issues
Decode error : If you are getting into this error, your account might have got restriction from spotify. Try removing it and add different one
The application may crash frequently as there is no proper exception handling yet. You can help by opening a new issue wih error message displayed on your console window after the application misbehaves.
The readme also needs to be written properly.

Fell free to open issues issue if you have bugs or feature requests
