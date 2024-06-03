from datetime import time, timedelta
import networkx as nx

def child_schedule() -> nx.DiGraph:
    """
    Generate a synthetic daily routine for an agent under the age of 16
    """

    G = nx.DiGraph()
    G.add_nodes_from(
        [
            ("home", {"leave_at": time(hour=8), "variation": timedelta(minutes=15)}),
            (
                "school",
                {
                    "leave_at": time(hour=15, minute=15),
                    "variation": timedelta(minutes=15),
                },
            ),
            (
                "supermarket",
                {"duration": timedelta(minutes=45), "variation": timedelta(minutes=15)},
            ),
            (
                "recreation",
                {"duration": timedelta(hours=2), "variation": timedelta(hours=1)},
            ),
            ("home 2", {"leave_at": time(hour=19), "variation": timedelta(hours=1)}),
        ]
    )
    G.add_edges_from(
        [
            ("home", "school", {"p": 1}),
            ("school", "home 2", {"p": 0.5}),
            ("school", "supermarket", {"p": 0.25}),
            ("school", "recreation", {"p": 0.25}),
            ("supermarket", "home 2", {"p": 1}),
            ("recreation", "home 2", {"p": 1}),
        ]
    )

    return G


def working_adult_schedule() -> nx.DiGraph:
    """
    Generate a synthetic daily routine for an agent aged 16-64 years
    """

    G = nx.DiGraph()
    G.add_nodes_from(
        [
            ("home", {"leave_at": time(hour=8), "variation": timedelta(minutes=15)}),
            (
                "school",
                {"duration": timedelta(minutes=10), "variation": timedelta(minutes=5)},
            ),
            ("shop", {"duration": timedelta(hours=2), "variation": timedelta(hours=1)}),
            (
                "work",
                {
                    "leave_at": time(hour=17, minute=15),
                    "variation": timedelta(minutes=15),
                },
            ),
            (
                "school 2",
                {"duration": timedelta(minutes=5), "variation": timedelta(minutes=1)},
            ),
            (
                "supermarket",
                {"duration": timedelta(minutes=45), "variation": timedelta(minutes=15)},
            ),
            ("home 2", {"leave_at": time(hour=19), "variation": timedelta(hours=1)}),
            (
                "recreation",
                {"duration": timedelta(hours=1), "variation": timedelta(minutes=30)},
            ),
            ("home 3", {"leave_at": time(hour=23), "variation": timedelta(hours=1)}),
        ]
    )
    G.add_edges_from(
        [
            ("home", "school", {"p": 1}),
            ("school", "shop", {"p": 0.1}),
            ("school", "work", {"p": 0.9}),
            ("shop", "work", {"p": 1}),
            ("work", "supermarket", {"p": 0.15}),
            ("work", "school 2", {"p": 0.6}),
            ("work", "home 2", {"p": 0.25}),
            ("supermarket", "home 2", {"p": 1}),
            ("school 2", "supermarket", {"p": 0.5}),
            ("school 2", "home 2", {"p": 0.5}),
            ("home 2", "recreation", {"p": 0.1}),
            ("home 2", "home 3", {"p": 0.9}),
            ("recreation", "home 3", {"p": 1}),
        ]
    )

    return G


def retired_adult_schedule() -> nx.DiGraph:
    """
    Generate a synthetic daily route for an agent ages 65 years plus
    """

    G = nx.DiGraph()
    G.add_nodes_from(
        [
            ("home", {"leave_at": time(hour=10), "variation": timedelta(hours=1)}),
            ("shop", {"duration": timedelta(hours=2), "variation": timedelta(hours=1)}),
            (
                "supermarket",
                {"duration": timedelta(minutes=45), "variation": timedelta(minutes=15)},
            ),
            (
                "recreation",
                {"duration": timedelta(hours=1), "variation": timedelta(minutes=30)},
            ),
            (
                "home 2",
                {"duration": timedelta(hours=2), "variation": timedelta(hours=1)},
            ),
            ("home 3", {"leave_at": time(hour=19), "variation": timedelta(hours=1)}),
        ]
    )
    G.add_edges_from(
        [
            ("home", "supermarket", {"p": 0.5}),
            ("home", "shop", {"p": 0.5}),
            ("supermarket", "home 2", {"p": 1}),
            ("shop", "home 2", {"p": 1}),
            ("home 2", "recreation", {"p": 0.5}),
            ("home 2", "home 3", {"p": 0.5}),
            ("recreation", "home 3", {"p": 1}),
        ]
    )

    return G


def get_schedule(agent_type: int) -> nx.DiGraph:
    """
    Return a synthetic daily routine based on agent type

        Args:
            agent_type (int): agent type identifier

    """

    match agent_type:
        case 0:
            return child_schedule()
        case 1:
            return working_adult_schedule()
        case 2:
            return retired_adult_schedule()
        case _:
            return working_adult_schedule()
