from ndlib.models.DiffusionModel import DiffusionModel
import numpy as np
import future.utils
from collections import defaultdict

__author__ = ["Alina Sirbu", "Giulio Rossetti"]
__email__ = ["alina.sirbu@unipi.it", "giulio.rossetti@isti.cnr.it"]


class AlgorithmicBiasModel(DiffusionModel):
    """
    Model Parameters to be specified via ModelConfig

    :param epsilon: bounded confidence threshold from the Deffuant model, in [0,1]
    :param gamma: strength of the algorithmic bias, positive, real

    Node states are continuous values in [0,1].

    The initial state is generated randomly uniformly from the domain [0,1].
    """

    def __init__(self, graph, seed=None):
        """
             Model Constructor

             :param graph: A networkx graph object
         """
        super(self.__class__, self).__init__(graph, seed)

        self.discrete_state = False

        self.available_statuses = {
            "Infected": 0
        }

        self.parameters = {
            "model": {
                "epsilon": {
                    "descr": "Bounded confidence threshold",
                    "range": [0, 1],
                    "optional": False
                },
                "gamma": {
                    "descr": "Algorithmic bias",
                    "range": [0, 100],
                    "optional": False
                }
            },
            "nodes": {},
            "edges": {}
        }

        self.name = "Agorithmic Bias"

        max_edgees = (self.graph.number_of_nodes() * (self.graph.number_of_nodes()-1))/2

        self.node_data = {}
        nids = np.array(list(self.status.items()))

        if max_edgees == self.graph.number_of_edges():
            self.ids = nids[:, 0]
            self.sts = nids[:, 1]

        else:
            for i in self.graph.nodes:
                i_neigh = list(self.graph.neighbors(i))
                i_ids = nids[:, 0][i_neigh]
                i_sts = nids[:, 1][i_neigh]
                self.node_data[i] = (i_ids, i_sts)

    def set_initial_status(self, configuration=None):
        """
        Override behaviour of methods in class DiffusionModel.
        Overwrites initial status using random real values.
        """
        super(AlgorithmicBiasModel, self).set_initial_status(configuration)

        # set node status
        for node in self.status:
            self.status[node] = np.random.random_sample()
        self.initial_status = self.status.copy()

    # def clean_initial_status(self, valid_status=None):
    #     for n, s in future.utils.iteritems(self.status):
    #         if s > 1 or s < 0:
    #             self.status[n] = 0

    # @staticmethod
    # def prob(distance, gamma, min_dist):
    #     if distance < min_dist:
    #         distance = min_dist
    #     return np.power(distance, -gamma)

    def iteration(self, node_status=True):
        """
        Execute a single model iteration

        :return: Iteration_id, Incremental node status (dictionary node->status)
        """
        # One iteration changes the opinion of N agent pairs using the following procedure:
        # - first one agent is selected
        # - then a second agent is selected based on a probability that decreases with the distance to the first agent
        # - if the two agents have a distance smaller than epsilon, then they change their status to the average of
        # their previous statuses

        actual_status = defaultdict(float)

        if self.actual_iteration == 0:
            self.actual_iteration += 1
            delta, node_count, status_delta = self.status_delta(self.status)
            if node_status:
                return {"iteration": 0, "status": self.status.copy(),
                        "node_count": node_count.copy(), "status_delta": status_delta.copy()}
            else:
                return {"iteration": 0, "status": {},
                        "node_count": node_count.copy(), "status_delta": status_delta.copy()}

        # interact with peers
        for n1 in self.graph.nodes: # range(0, self.graph.number_of_nodes()):
            # select a random node
            # n1 = list(self.graph.nodes)[np.random.randint(0, self.graph.number_of_nodes())]

            # select all node's neighbours (no digraph possible)
            neighbours = list(self.graph.neighbors(n1))

            if len(neighbours) == 0:
                continue

            if len(self.node_data) == 0:
                sts = self.sts
                ids = self.ids
            else:
                ids = self.node_data[n1][0]
                sts = self.node_data[n1][1]

            f = lambda x, y: np.power(np.maximum(np.abs(x-y),  np.full(x.shape[0], 0.00001)), -self.params['model']['gamma'])
            selection_prob = f(sts, self.status[n1])

            # compute probabilities to select a second node among the neighbours
            total = np.sum(selection_prob)
            selection_prob = selection_prob / total

            cumulative_selection_probability = np.cumsum(selection_prob)
            r = np.random.random_sample()
            n2 = np.argmax(cumulative_selection_probability >= r) - 1
            n2 = ids[n2]

            # update status of n1 and n2
            diff = np.abs(self.status[n1] - self.status[n2])
            if diff < self.params['model']['epsilon']:
                avg = (self.status[n1] + self.status[n2]) / 2.0
                actual_status[n1] = avg
                actual_status[n2] = avg

        delta, node_count, status_delta = self.status_delta(actual_status)
        self.status = actual_status
        self.actual_iteration += 1

        if node_status:
            return {"iteration": self.actual_iteration - 1, "status": delta.copy(),
                    "node_count": node_count.copy(), "status_delta": status_delta.copy()}
        else:
            return {"iteration": self.actual_iteration - 1, "status": {},
                    "node_count": node_count.copy(), "status_delta": status_delta.copy()}
