import networkx as nx
import pyplot as plt


class GraphAnalyzer:
    @staticmethod
    def graph(mods):

        DG = nx.DiGraph()

        ignore = ["brrainz.harmony", "UnlimitedHugs.HugsLib"]
        for m in mods:
            if m.after:
                for a in m.after:
                    if a in mods:
                        if not a in ignore and not m.packageid in ignore:
                            DG.add_edge(a, m.packageid)
            if m.before:
                for b in m.before:
                    if b in mods:
                        if not b in ignore and not m.packageid in ignore:
                            DG.add_edge(m.packageid, b)

        pos = nx.spring_layout(DG, seed=56327, k=0.8, iterations=15)
        nx.draw(
            DG,
            pos,
            node_size=100,
            alpha=0.8,
            edge_color="r",
            font_size=8,
            with_labels=True,
        )
        ax = plt.gca()
        ax.margins(0.08)

        print("topological sort:")
        sorted = list(nx.topological_sort(DG))
        for n in sorted:
            print(n)

        plt.show()
