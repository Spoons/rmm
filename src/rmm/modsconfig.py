#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast
from xml.etree import ElementTree as ET

import rmm.util as util
from rmm.mod import Mod


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
                list[str],
                util.list_grab("activeMods", self.root),
            )
            self.mods = [Mod(packageid=pid) for pid in enabled]
        except TypeError:
            print("Unable to parse activeMods in ModsConfig")
            raise
        self.version = util.element_grab("version", self.root)
        self.length = len(self.mods)

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
                new_element.text = mod.packageid
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

    def expansions(self):
        pass

    def enable_mod(self, m: Mod):
        self.mods.append(m)

    def remove_mod(self, m: Mod):
        for k, _ in enumerate(self.mods):
            if self.mods[k] == m:
                del self.mods[k]

    def autosort(self, mods, config):
        import json

        import networkx as nx

        DG = nx.DiGraph()

        before_core = ["brrainz.harmony", "me.samboycoding.betterloading"]

        expansion_load_order = [
            "ludeon.rimworld",
            "ludeon.rimworld.royalty",
            "ludeon.rimworld.ideology",
        ]

        combined_load_order = before_core + expansion_load_order
        for n, pid in enumerate(combined_load_order):
            if pid not in self.mods:
                del combined_load_order[n]

        for k in range(0, len(combined_load_order)):
            for j in range(k + 1, len(combined_load_order)):
                DG.add_edge(combined_load_order[j], combined_load_order[k])

        populated_mods = [m for m in mods if m in self.mods]

        with (config.game_path / "1847679158/db/communityRules.json").open("r") as f:
            community_db = json.load(f)

        for pid in populated_mods:
            try:
                for j in community_db["rules"][pid.packageid]["loadAfter"]:
                    if j:
                        try:
                            pid.before.add(j)
                        except AttributeError:
                            pid.before = set(j)
            except KeyError:
                pass
            try:
                for j in community_db["rules"][pid.packageid]["loadBefore"]:
                    if j:
                        try:
                            pid.after.add(j)
                        except AttributeError:
                            pid.after = set(j)
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

        for m in populated_mods:
            if rocketman and m.packageid != "krkr.rocketman":
                DG.add_edge("krkr.rocketman", m.packageid)
            if not m in combined_load_order:
                for n in combined_load_order:
                    DG.add_edge(m.packageid, n)
            if m.after:
                for a in m.after:
                    if a in self.mods:
                        DG.add_edge(a.lower(), m.packageid)
            if m.before:
                for b in m.before:
                    if b in self.mods:
                        DG.add_edge(m.packageid, b.lower())

        count = 0
        while True:
            try:
                sorted_mods = reversed(list(nx.topological_sort(DG)))
                self.mods = [Mod(packageid=n) for n in sorted_mods]
                print("Auto-sort complete")
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
