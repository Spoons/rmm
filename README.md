# RMM: RimWorld Mod Manager

Do you dislike DRM based platforms but love RimWorld and it's mods? RMM is cross platform mod manager that allows you to download, update, auto-sort, and configure mods for the game without relying on the Steam consumer client. RMM has a keyboard based interface that is easy to use and will be familiar to Linux users and developers. 

RMM v1.0 supports Windows, Linux, and MacOS. 

## Prerequisites 

To use RMM you need:
- SteamCMD installed and in your path. (Linux/Mac Only)
- Set RMM_PATH to game path if game is installed to a not default location.
- Python 3.9+

# Installation for Windows
1. Install latest Python 3 release from `https://www.python.org/downloads/windows/`
   - Ensure 'add to PATH' is checked / enabled during installation.

2. Open 'cmd' with Administrator privileges and type `python -m pip install --user rmm-spoons`
   - Use with `python -m rmm`

3. (Optional) Add `C:\Users\[username]\AppData\Roaming\Python\[version]\Scripts\` to PATH.
    - Use with `rmm`
   
# Installation for MacOS:
1. Install Python3 with brew.
2. `pip3 install --user rmm-spoons`
3. Use with `python3 -m rmm`
4. Add python bin directory to your path:
``` sh
echo "export PATH=\"$PATH:$HOME/Library/Python/$(python3 --version | awk '{split($2,a,".") ; print a[1] "." a[2] }')/bin\"" >> ~/.zshrc
```
5. Use with `rmm`

## Upgrading on MacOS
Please perodically update RMM with the following command:
`pip3 install --upgrade rmm-spoons`

# Installation for Arch Linux

RMM has an AUR package 'rmm'. The package brings in all dependencies, including steamcmd, and can be installed with makepkg and git or an AUR helper as shown below. No other steps are required:

## Makepkg
``` sh
mkdir -p ~/build ; cd ~/build
git clone https://aur.archlinux.org/rmm.git
cd rmm
makepkg -si
```

## Yay (AUR helper)
``` sh
yay -S rmm
```


# Installation for other Linux distributions (via PyPi)

## 1. Installing SteamCMD on Ubuntu
``` sh
sudo su -c 'apt update && apt upgrade && apt install software-properties-common && add-apt-repository multiverse && dpkg --add-architecture i386 && apt update && apt install lib32gcc1 steamcmd' ; 
echo 'export PATH="$PATH:/usr/games' >> ~/.bashrc ;
exec $SHELL
```

## 1. Installing SteamCMD on Debian
``` sh
sudo su -c 'apt update && apt upgrade && apt install software-properties-common && add-apt-repository non-free && dpkg --add-architecture i386 && apt update && apt install steamcmd' ; 
echo 'export PATH="$PATH:/usr/games' >> ~/.bashrc ;
exec $SHELL
```


## 2. Adding .local/bin to your PATH
RMM can be directly accessed with command `rmm`. In order for this to work, you need to add `~/.local/bin` to your PATH variable, otherwise, your terminal will not find the `rmm` script. If you notice that you cannot run `rmm` after installation, try the following:

``` sh
echo 'export PATH="$PATH:$HOME/.local/bin" >> ~/.bashrc ; exec $SHELL
```

Alternatively, RMM can always called with:
``` sh
python -m rmm
```

## 3. Installing package from PIP
``` sh
python -m pip install --user rmm-spoons
```

## Upgrading with PIP
Please perodically update RMM with the following command:
`python -m pip install --user --upgrade rmm-spoons`

# Configuration
## Set RMM_PATH (Optional)
If RimWorld is installed a directory other than the default ones, you should set the RMM_PATH variable to your game directory for convenience.

Set it permanently in your `bashrc` or `zshrc` files:
``` sh
# Note please update this path to your actual game or mod directory
echo 'export RMM_PATH="$HOME/your/game/path" >> ~/.bashrc ; 
exec $SHELL
```

Temporarily set it during your shell session:
``` sh
export RMM_PATH="~/PATHTOGAME/game/Mods"
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
rmm [options] enable [-a]|[-f file]|<packageid>|<term>
rmm [options] disable [-a]|[-f file]|<packageid>|<term>
rmm [options] remove [-a]|[-f file]|<packageid>|<term>
rmm [options] list
rmm [options] query [<term>]
rmm [options] search <term>
rmm [options] sort
rmm [options] sync <name>
rmm [options] update
rmm [options] verify

rmm -h | --help
rmm -v | --version

Operations:
config            Sort and enable/disable mods with ncurses
export            Save mod list to file.
import            Install a mod list from a file.
list              List installed mods.
query             Search installed mods.
remove            Remove installed mod.
search            Search Workshop.
sort              Auto-sort your modlist
sync              Install or update a mod.
update            Update all mods from Steam.
verify            Checks that enabled mods are compatible
enable            Enable mods
disable           Disable mods
order             Lists mod order

Parameters
term              Name, author, steamid
file              File path for a mod list
name              Name of mod.

Flags
-a                Performs operation on all mods
-d                Export disabled mods to modlist.
-e                Export enabled mods to modlist.
-f                Specify mods in a mod list

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

Tip:
You can use enable, disable, and remove with no
argument to select from all mods.
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

Removing all / a range packages:

``` sh
rmm remove 
# all packages will be listed. specify your desired range at the interactive prompt.
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

Auto sort mods:
``` sh
rmm sort
```

Manually sort mods:
``` sh
rmm config
```

Show mod load order:

``` sh
rmm order
```

### Tips
1. Duplicating a mod setup to a new installation:
``` sh
rmm -p ~/path-to-game export ~/modlist.txt
rmm -p ~/path-to-game import ~/modlist.txt
```

2. It is recommended to auto sort your mods after installation of a mod or modlist.

# Related Projects
- [rwm](https://github.com/AOx0/rwm): Rust rewrite of RMM.

# Contributing
If you would like to contribute your time or efforts towards the project, you are welcome to and your efforts will be appreciated. Please format any code changes through python-black.

# License
This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details

