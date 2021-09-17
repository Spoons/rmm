# RMM: Rimworld Mod Manager

RMM is an open source RimWorld mod manager designed for Unix systems. RMM uses the SteamCMD binary to download mods. 



## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. Improvements in this process will follow. 

### Prerequisites

To use RMM you need:
1. steamcmd in your PATH
2. requests and bs4 python library
3. set RMM_PATH to your RimWorld mod directory.

---

1. For Arch Linux, you can install steamcmd as stated below:
```
mkdir -p ~/build ; cd ~/build
git clone https://aur.archlinux.org/steamcmd.git
cd steamcmd
makepkg -si
```

2. Install python libraries in pip user directory:
```
pip install --user -r requirements.txt
```

3. Append following to your .zshrc or .bashrc config. Replace 'PATHTOGAME' with the path that leads to your 'rimworld' directory.
```
export RMM_PATH="~/PATHTOGAME/game/Mods"
```

### Installing

Clone repository and link core.py into your PATH.
```
mkdir -p ~/build
git clone https://github.com/Spoons/rmm.git ~/build/rmm
cd ~/build/rmm
sudo ln -s $(HOME)/build/rmm/core.py /usr/local/bin/rmm
```

### Useage

List installed packages:
``` 
rmm list
```

Search workshop packages:
``` 
rmm search modname
```

Install package:
```
rmm sync rimhud
```

Install mod list:
```
rmm sync -f ~/pathtomodlist
```

Update all packages:
```
rmm update
```

Backup mod directory:
```
rmm backup ~/rimworld.tar
```

Export mod list:
```
rmm export ~/modlist
```

## License

This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details

