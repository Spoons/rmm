# RMM: Rimworld Mod Manager

RMM is an open source RimWorld mod manager designed for Unix systems. RMM uses the SteamCMD binary to download mods. 

## Installation

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. Improvements in this process will follow. 

### Prerequisites

To use RMM you need:

- SteamCMD installed and in your path.
- set RMM_PATH to your RimWorld mod directory.

#### Install SteamCMD

1. A. For Arch Linux, you can install steamcmd using makepkg as stated below:
``` sh
mkdir -p ~/build ; cd ~/build
git clone https://aur.archlinux.org/steamcmd.git
cd steamcmd
makepkg -si
```

1. B. Alternatively, you can install it using a 'AUR Helper' such as yay.
``` sh
yay -S steamcmd
```

2. Verify steamcmd is correctly installed:
``` sh
whereis steamcmd
```

Should return a path such as below. Otherwise check to make sure steamcmd is in your path.
``` sh
steamcmd: /usr/bin/steamcmd /usr/share/steamcmd
```

#### Adding .local/bin to your PATH

RMM can be directly accessed with command `rmm`. In order for this to work, you need to add `~/.local/bin` to your PATH variable, otherwise, your terminal will not find the `rmm` script. If you notice that you cannot run `rmm` after installation, try the following:
``` sh
echo 'export PATH="$PATH:$HOME/.local/bin" >> ~/.bashrc
```

Alternatively, RMM can always be accessed by
``` sh
python -m rmm
```


#### Set RMM_PATH (Optional)

RMM will first search for the default GOG games installation directory, steamcache folder, before falling back to an error message if this value is not set. This value takes precedence over those defaults. I recommend setting this variable.

1. A. Set RMM_PATH variable to the 'Mods' sub directory in your Rimworld game folder in your .bashrc or .zshrc. For example:

``` sh
# Note please update this path to your actual game or mod directory
echo 'export RMM_PATH="$HOME/GOG\ Games/RimWorld" >> ~/.bashrc
```

1. B. Alternatively, you can change this path at runtime. This is useful when managing multiple copies of the games.

``` sh
export RMM_PATH="~/PATHTOGAME/game/Mods"
rmm list
# or you can use
RMM_PATH="~/PATHTOGAME/game/Mods" rmm list
```

#### Set RMM_WORKSHOP_PATH (Optional)

RMM supports managing mods in your Steam Workshop mods directory. If RimWorld is installed into the same library as your workshop mods, RMM will automatically find your workshop mods folder and assign it automatically. If you run `rmm list` and see, 'workshop path: /workshop/filepath', then you know this is occurring. You typically will not need to set this variable.

``` sh
echo 'export RMM_WORKSHOP_PATH="$HOME/.local/share/Steam/steamapps/workshop" >> ~/.bashrc
```

### Install from PyPi (Recommended)

``` sh
python3 -m pip install --user rmm-spoons
```


### Installation for Development

Clone repository and install with setuptools editable mode.
```
mkdir -p ~/build
git clone https://github.com/Spoons/rmm.git ~/build/rmm
pip install --user ~/build/rmm
```

## Useage

List installed packages:
``` 
rmm list
```

Search workshop packages:
``` 
rmm search modname
```

Search locally installed mods
``` 
rmm query modname
```

Install package:
```
rmm sync rimhud
```

Removing a package:
```
rmm remove fuzzy
```

Saving a mod list
```
rmm export ~/modlist.txt
```

Install mod list:
```
rmm sync -f ~/modlist.txt
```

Update all packages:
```
rmm update
```

Backup mod directory:
```
rmm backup ~/rimworld.tar
```

### Tips
Duplicating a mod setup to a new installation:
``` sh
RMM_PATH=~/path/to/oldgame/game/Mods rmm export ~/modlist.txt
RMM_PATH=~/path/to/newgame/game/Mods rmm sync -f ~/modlist.txt
```

## License

This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details

