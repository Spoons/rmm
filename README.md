# RMM: RimWorld Mod Manager


[![RMM](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/rmm-spoons/main/assets/badge/v2.json)](https://github.com/spoons/rmm)
[![image](https://img.shields.io/pypi/v/rmm-spoons.svg)](https://pypi.python.org/pypi/rmm-spoons)
[![image](https://img.shields.io/pypi/l/rmm-spoons.svg)](https://pypi.python.org/pypi/rmm-spoons)
[![image](https://img.shields.io/pypi/pyversions/rmm-spoons.svg)](https://pypi.python.org/pypi/rmm-spoons)
[![Actions status](https://github.com/spoons/rmm/workflows/CI/badge.svg)](https://github.com/spoons/rmm/actions)

A mod manager for RimWorld.

- 🌍 Cross-platform: Supports Linux, MacOS, Windows
- 🎮 Broad Game Source Support: Steam, GOG, and DRM-free installations
- 🔗 RimWorld Versions: Seamlessly supports 1.0 and above
- 🚀 Fetch Directly: Installs and updates mods from the Steam Workshop
- 🛡️ No Strings Attached: Operate without a Steam account
- 📑 Modlists: Organize, activate, deactivate with ease
- 🔄 Stay Updated: Automatic mod updates at your fingertips
- 🧩 Smart Sorting: Auto-arrange mods for optimal load order
- ❌ Simplified Cleanup: Easy mod deactivation and removal
- 📦 Always Safe: Mod backup and restore features
- ↕️ Import/Export: Convenient modlist transitions and sharing
- 🧰 Flexible and User-Friendly: Customizable paths, settings, and configurations

RMM aims to allow subscribing to and managing mods for RimWorld without a Steam account or have installed the game with
a DRM-free installer.

## Table of Contents
1. [Getting Sarted](#getting-started)
1. [Detailed Installation Guide](#detailed-installation-guide)
   1. [Windows](#windows)
   1. [MacOS](#macos)
   1. [Arch Linux](#arch-linux)
   1. [Other Linux Distributions](#installation-for-other-linux-distributions-via-pypi)
1. [Configuration](#configuration)
1. [Usage](#usage)
1. [Tips](#tips)
1. [Contributing](#contributing)
1. [License](#license)

## Getting Started
RMM is available at [`rmm`](https://pypi.org/project/rmm-spoons/) on PyPi. To install, run:

```shell
pip install rmm-spoons
```
Ensure that SteamCMD is set up and appended to your path. (Required for Linux/Mac only)

## Detailed Installation Guide
### Windows

1. Fetch and install the most recent Python 3 release from Python's official website. During the installation, make sure to select 'add to PATH'.
   With administrative rights, launch the Command Prompt and input:

1. ```shell
   python -m pip install --user rmm-spoons
   ```
1. (Optional) Append C:\Users\[username]\AppData\Roaming\Python\[version]\Scripts\ to your PATH to use with just rmm.

### MacOS

1. Utilize brew to install Python3:

   ```shell
   brew install python3
   ```
2. To install RMM:
   ```shell
   pip3 install --user rmm-spoons
   ```
3. Add Python's bin directory to your path:
   ```shell
    echo "export PATH=\"$PATH:$HOME/Library/Python/$(python3 --version | awk '{split($2,a,".") ; print a[1] "." a[2] }')/bin\"" >> ~/.zshrc
   ```
### Arch Linux
RMM is accessible via the AUR package 'rmm'. 


- Using Paru (AUR helper)
   ```sh
   yay -S rmm
   ```

## Installation for Other Linux Distributions (via PyPi)

Detailed instructions are provided for Ubuntu and Debian. Kindly consult your distribution's documentation if you use a
different Linux variant:

### Installing SteamCMD on Ubuntu

```sh
sudo su -c 'apt update && apt upgrade && apt install software-properties-common && add-apt-repository multiverse && dpkg --add-architecture i386 && apt update && apt install lib32gcc1 steamcmd' 
echo 'export PATH="$PATH:/usr/games' >> ~/.bashrc
exec $SHELL
```

### Installing SteamCMD on Debian

```sh
sudo su -c 'apt update && apt upgrade && apt install software-properties-common && add-apt-repository non-free && dpkg --add-architecture i386 && apt update && apt install steamcmd'
echo 'export PATH="$PATH:/usr/games' >> ~/.bashrc
exec $SHELL
```

### Installing RMM via PyPi

Install RMM via PyPi:
``` sh
python -m pip install --user rmm-spoons
```

If you encounter a unknown command error, add the following to your .bashrc:
```sh
echo 'export PATH="$PATH:$HOME/.local/bin" >> ~/.bashrc
exec $SHELL
```


## Configuration
### Setting RMM_PATH (Optional)

If RimWorld isn't in its default directory, it's advisable to set the RMM_PATH environment variable pointing to your
game directory. This can be achieved in two ways:

**Permanently**: Edit your shell profile (bashrc, zshrc):

```sh
echo 'export RMM_PATH="$HOME/your/game/path"' >> ~/.bashrc
exec $SHELL
```

**Temporarily**: Only for the current shell session:

```sh
export RMM_PATH="~/PATHTOGAME/game/Mods"
```

## Usage
List installed packages:
```  sh
rmm list
```

Search workshop packages:
```  sh
rmm search term
```

Search locally installed mods
```  sh
rmm query term
```

Install package:
``` sh
rmm sync rimhud
```

Removing a package:
``` sh
rmm remove fuzzy
```

Removing all / a range packages:

``` sh
rmm remove 
# all packages will be listed. specify your desired range at the interactive prompt.
```

Saving a mod list
``` sh
rmm export ~/modlist.txt
```

Install mod list:
``` sh
rmm import ~/modlist.txt
```

Update all packages:
``` sh
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

## Tips
1. Duplicating Mod Setups: If you're aiming to replicate a mod setup on a fresh installation:
```sh
rmm -p ~/path-to-current-game export ~/modlist.txt
rmm -p ~/path-to-new-game import ~/modlist.txt
```


## Contributing

Passionate about RMM and have ideas to contribute? We're all ears! To maintain code quality, we kindly request that any code alterations be formatted using python-black. For more details, check our Contribution Guidelines.


## License
RMM is open-sourced under the GPLv3 License. Dive into the LICENSE file for thorough details.
