#!/usr/bin/env python3

from pathlib import Path
from typing import List, cast
from xml.etree import ElementTree as ET

from . import util
from .mod import EXPANSION_PACKAGES, Mod


class ModsConfig:
    def __init__(self, p: Path):
        if isinstance(p, str):
            p = Path(p)
        self.path = p.expanduser()
        try:
            self.element_tree = ET.parse(self.path)
        except OSError:
            print("Unable to read ModsConfig file at " + str(self.path))
            raise

        self.root = self.element_tree.getroot()
        try:
            enabled = cast(
                List[str],
                util.list_grab("activeMods", self.root),
            )
            # self.mods = [Mod(packageid=pid) for pid in enabled]
            self.mods = {pid: None for pid in enabled}
        except TypeError:
            print("Unable to parse activeMods in ModsConfig")
            raise
        self.version = util.element_grab("version", self.root)
        self.length = len(self.mods)
        try:
            self.expansions = util.list_grab("knownExpansions", self.root)
            if not self.expansions:
                self.expansions = []
        except TypeError:
            self.expansions = []

    def write(self):
        active_mods = self.root.find("activeMods")
        if not active_mods:
            return
        try:
            for item in list(active_mods.findall("li")):
                if active_mods:
                    active_mods.remove(item)
        except AttributeError:
            pass

        try:
            for mod in self.mods:
                new_element = ET.SubElement(active_mods, "li")
                new_element.text = mod
        except AttributeError:
            raise Exception("Unable to find 'activeMods' in ModsConfig")

        buffer = util.et_pretty_xml(self.root)

        try:
            with self.path.open("w+") as f:
                f.seek(0)
                f.write(buffer)
        except OSError:
            print("Unable to write ModsConfig")
            raise

    def enable_mod(self, m: Mod):
        self.mods[m.packageid] = None

    def disable_mod(self, m: Mod):
        if m.packageid in self.mods:
            del self.mods[m.packageid]

    def autosort(self, mods, config):
        import json

        import networkx as nx

        DG = nx.DiGraph()

        before_core = ["brrainz.harmony", "me.samboycoding.betterloading"]

        core = ["ludeon.rimworld"]

        expansion_load_order = [
            "ludeon.rimworld.royalty",
            "ludeon.rimworld.ideology",
        ]

        combined_load_order = before_core + core + expansion_load_order
        for n, pid in enumerate(combined_load_order):
            if not pid in self.mods:
                del combined_load_order[n]

        for k in range(0, len(combined_load_order)):
            for j in range(k + 1, len(combined_load_order)):
                DG.add_edge(combined_load_order[j], combined_load_order[k])

        populated_mods = {m.packageid: m for m in mods if m in self.mods}

        rules_path = Path(
            config.mod_path / "rupal.rimpymodmanagerdatabase/db/communityRules.json"
        )
        if not rules_path.is_file():
            print("Downloading rules file\n")
            # import rmm.steam
            # rules_cache_path = Path(SteamDownloader.find_path()[1]/ "1847679158")
            # rmm.steam.SteamDownloader.download([1847679158])

            manager.Manager(config).sync_mods([Mod(steamid=1847679158)])

        with (
            config.mod_path / "rupal.rimpymodmanagerdatabase/db/communityRules.json"
        ).open("r", encoding="utf-8") as f:
            community_db = json.load(f)

        for pid, m in populated_mods.items():
            try:
                for j in community_db["rules"][m.packageid]["loadAfter"]:
                    if j:
                        try:
                            m.before.add(j)
                        except AttributeError:
                            m.before = set(j)
            except KeyError:
                pass
            try:
                for j in community_db["rules"][m.packageid]["loadBefore"]:
                    if j:
                        try:
                            m.after.add(j)
                        except AttributeError:
                            m.after = set(j)
            except KeyError:
                pass

        rocketman = False
        if "krkr.rocketman" in populated_mods:
            rocketman = True

        if (
            "murmur.walllight" in populated_mods
            and "juanlopez2008.lightsout" in populated_mods
        ):
            DG.add_edge("juanlopez2008.lightsout", "murmur.walllight")

        mods_for_removal = {
            n
            for n in expansion_load_order + before_core
            if n not in EXPANSION_PACKAGES + mods or n not in self.mods
        }

        for pid, m in populated_mods.items():
            if rocketman and pid != "krkr.rocketman":
                DG.add_edge("krkr.rocketman", pid)
            if not m in combined_load_order:
                for n in combined_load_order:
                    DG.add_edge(pid, n)
            if m.after:
                for a in m.after:
                    if a in self.mods:
                        DG.add_edge(a.lower(), pid)
            if m.before:
                for b in m.before:
                    if b in self.mods:
                        DG.add_edge(pid, b.lower())

        count = 0
        while True:
            try:
                sorted_mods = reversed(list(nx.topological_sort(DG)))
                self.mods = [n for n in sorted_mods]
                self.mods = util.list_loop_exclusion(self.mods, mods_for_removal)
                print("Auto-sort complete")

                print(
                    "Verifying state: {}".format(
                        "good" if self.verify_state(populated_mods) else "bad"
                    )
                )
                return
            except nx.exception.NetworkXUnfeasible:
                if count >= 10:
                    print("Unable to break cycles")
                    exit(0)
                print("Cycle found. Breaking load order cycle")
                cycle = nx.find_cycle(DG)
                print(cycle)
                DG.remove_edge(*cycle[0])
                count += 1

    def verify_state(self, mods: List[Mod]):
        if isinstance(mods, list):
            populated_mods = {m.packageid: m for m in mods if m.packageid in self.mods}
        elif isinstance(mods, dict):
            populated_mods = {
                m.packageid: m for m in mods.values() if m.packageid in self.mods
            }
        else:
            raise Exception("bad data type")

        incompatible = dict()
        for m in populated_mods.values():
            try:
                for n in m.incompatible:
                    incompatible[n] = None
            except TypeError:
                pass

        for n in populated_mods:
            if n in incompatible:
                return False

        return True
