# RMM: RimWorld Mod Manager

Do you dislike DRM based platforms but love RimWorld and it's mods? RMM is cross platform mod manager that allows you to download, update, auto-sort, and configure mods for the game without relying on the Steam consumer client. RMM has a keyboard based interface that is easy to use and will be familiar to Linux users and developers. 

RMM v1.0 supports Windows, Linux, and MacOS. 

## Prerequisites

To use RMM you need:
- SteamCMD installed and in your path.
- Set RMM_PATH to game path if game is installed in non default location.

# Installation for Arch Linux

RMM has an AUR package 'rmm'. The package brings in all dependencies, including steamcmd, and can be installed with makepkg and git or an AUR helper as shown below. No other steps are required:

a. Makepkg:
``` sh
mkdir -p ~/build ; cd ~/build
git clone https://aur.archlinux.org/rmm.git
cd rmm
makepkg -si
```

b. yay (AUR Helper)
``` sh
yay -S rmm
```


# Installation via PIP (PyPi)

## 1. Install SteamCMD

For Arch Linux, you can install steamcmd using makepkg as stated below:
``` sh
mkdir -p ~/build ; cd ~/build
git clone https://aur.archlinux.org/steamcmd.git
cd steamcmd
makepkg -si
```

Alternatively, you can install it using a 'AUR Helper' such as yay.
``` sh
yay -S steamcmd
```

Verify steamcmd is correctly installed with the below command:
``` sh
whereis steamcmd
```

`whereis` should return a path such as below. Otherwise, ensure steamcmd is in your PATH.
``` sh
steamcmd: /usr/bin/steamcmd /usr/share/steamcmd
```

## 2. Adding .local/bin to your PATH

RMM can be directly accessed with command `rmm`. In order for this to work, you need to add `~/.local/bin` to your PATH variable, otherwise, your terminal will not find the `rmm` script. If you notice that you cannot run `rmm` after installation, try the following:

``` sh
echo 'export PATH="$PATH:$HOME/.local/bin" >> ~/.bashrc
```

Alternatively, RMM can always called with:

``` sh
python -m rmm
```

## 3. Installing package from PIP

``` sh
python3 -m pip install --user rmm-spoons
```

# Configuration
## Set RMM_PATH (Optional)

If RimWorld is installed a directory other than the default ones, you should set the RMM_PATH variable to your game directory for convenience.

Set it permanently in your `bashrc` or `zshrc` files:
``` sh
# Note please update this path to your actual game or mod directory
echo 'export RMM_PATH="$HOME/your/game/path" >> ~/.bashrc
```

Temporarily set it during your shell session:
``` sh
export RMM_PATH="~/PATHTOGAME/game/Mods"
```

## Set RMM_WORKSHOP_PATH (Optional)

You probably do not need to set this variable.

RMM supports managing mods in your Steam Workshop mods directory. If RimWorld is installed into the same library as your Workshop mods, as would be the case for most people, RMM will find your workshop directory. Otherwise, you can set this value as per the example below:

``` sh
echo 'export RMM_WORKSHOP_PATH="$HOME/.local/share/Steam/steamapps/workshop" >> ~/.bashrc
```

# Installation for Development (Developers)

Clone repository and install with pip.
```
mkdir -p ~/build
git clone https://github.com/Spoons/rmm.git ~/build/rmm
pip install --user ~/build/rmm
```

# Usage
```
RimWorld Mod Manager

Usage:
rmm [options] config
rmm [options] export [-e]|[-d] <file>
rmm [options] import <file>
rmm [options] list
rmm [options] query [<term>...]
rmm [options] remove [-f file]|[<term>...]
rmm [options] search <term>...
rmm [options] sort
rmm [options] sync <name>...
rmm [options] update [sync options]
rmm -h | --help
rmm -v | --version

Operations:
config            Sort and enable/disable mods
export            Save mod list to file.
import            Install a mod list from a file.
list              List installed mods.
query             Search installed mods.
remove            Remove installed mod.
search            Search Workshop.
sort              Auto-sort your modslist
sync              Install or update a mod.
update            Update all mods from Steam.

Parameters
term              Name, author, steamid
file              File path
name              Name of mod.

Export Option:
-d                Export disabled mods to modlist.
-e                Export enabled mods to modlist.

Remove Options:
-f                Remove mods listed in modlist.

Options:
-p --path DIR     RimWorld path.
-w --workshop DIR Workshop Path.
-u --user DIR     User config path.

Environment Variables:
RMM_PATH          Folder containings Mods
RMM_WORKSHOP_PATH Folder containing Workshop mods (optional)
RMM_USER_PATH     Folder containing saves and config

Pathing Preference:
CLI Argument > Environment Variable > Defaults
```

## How To
List installed packages:
``` 
rmm list
```

Search workshop packages:
``` 
rmm search term
```

Search locally installed mods
``` 
rmm query term
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
rmm import ~/modlist.txt
```

Update all packages:
```
rmm update
```

Backup mod directory:
```
rmm backup ~/rimworld.tar
```

Migrate from Steam Workshop to RimWorld 'Mods' folder:
``` 
rmm migrate
```


### Tips
Duplicating a mod setup to a new installation:
``` sh
rmm -p ~/path-to-game export ~/modlist.txt
rmm -p ~/path-to-game import ~/modlist.txt
```

# Contributing
If you would like to contribute your time or efforts towards the project, you are welcome to and your efforts will be appreciated. Please format any code changes through python-black.

# License
This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details

