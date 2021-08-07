import subprocess
import shlex
import os
import xml.etree.ElementTree as ET


class Mod:
    def __init__(self, name, steamid, versions, author, fp):
        self.name = name
        self.versions = versions
        self.author = author
        self.steamid = steamid
        self.fp = fp
    def __repr__(self):
        return "<Mod name:{} author:{} steamid:{} versions:{}>".format(self.name, self.author, self.steamid, self.versions)

def create_modlist_from_folder(filepath):
    mods = []
    for dirs in os.listdir(filepath):
        mods.append(create_mod_from_dir(filepath+"/"+dirs))
    return mods

def create_mod_from_dir(filepath):
    tree = ET.parse(filepath + "/About/About.xml")
    root = tree.getroot()
    name = root.find('name').text
    author = root.find('author').text
    versions = [v.text for v in root.find('supportedVersions').findall('li')]
    with open(filepath+"/About/PublishedFileId.txt") as f:
        steamid = f.readline().strip()

    return Mod(name, steamid, versions, author, filepath)


def read_modlist(filepath):
    mods = []
    with open(filepath) as f:
        for line in f:
            itemid = line.split("#", 1)[0]
            try:
                mods.append(int(itemid))
            except ValueError:
                continue

    return mods

def workshop_format(mods):
    return (s := ' +workshop_download_item 294100 ') + s.join(str(x) for x in mods)

def download(mods, folder):
    query = "steamcmd +login anonymous +force_install_dir \"{}\" \"{}\" +quit".format(folder, workshop_format(mods))
    with subprocess.Popen(shlex.split(query), shell=False,
                          stdout=subprocess.PIPE, bufsize=-1, close_fds=True) as proc:
        for line in iter(proc.stdout.readline, b''):
            print(line.decode('utf-8'), end='')

def download_modlist(mods, path):
    steamids = [n.steamid for n in mods]
    return download(steamids, path)

mods = create_modlist_from_folder("/home/miffi/apps/rimworld/game/Mods")
download_modlist(mods, "/tmp")
