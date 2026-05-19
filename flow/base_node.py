import numpy as np


class BaseNode:
    def __init__(self, *args):
        if len(args) == 6:
            if callable(args[3]):
                parentFlow = None
                nodeName, parentNode, nextNode, actionFunction, parameter, isRootNode = args
            else:
                parentFlow, nodeName, parentNode, nextNode, actionFunction, isRootNode = args
                parameter = None
        elif len(args) == 5:
            parentFlow = None
            nodeName, parentNode, nextNode, actionFunction, isRootNode = args
            parameter = None
        else:
            raise TypeError(
                "BaseNode expects either 5 legacy arguments or 6 arguments including parentFlow"
            )

        self.parentFlow = parentFlow
        self.nodeName = nodeName
        self.parentNode = parentNode
        self.nextNode = nextNode
        self.actionFunction = actionFunction
        self.parameter = parameter
        self.isRootNode = isRootNode
        self.fullRes = {}

    def setRootNode(self, isRootNode: bool):
        self.isRootNode = isRootNode

    def setParentNode(self, node):
        self.parentNode = node
        node.nextNode = self

    def setNextNode(self, node):
        self.nextNode = node
        node.parentNode = self

    def setParameter(self, parameter):
        self.parameter = parameter

    def executeAction(self):
        try:
            parameter_length = len(self.parameter)
        except TypeError:
            parameter_length = 0

        print(
            "-----------------------",
            "Node Name: ",
            self.nodeName,
            " | Parameter:  ",
            self.parameter,
            "(Length:",
            parameter_length,
            ")",
            "-----------------------",
        )
        result = self.actionFunction(self.parameter)
        print("Node actionFunction Result: ", result)
        self.fullRes = result
        if isinstance(result, (list, tuple, np.ndarray)):
            # 决策节点约定返回 [传给下个节点的数据, 分支键]。
            load = result[0]
            print("Decider Node Load", load, " | Decider Node resultMapper: ", result[1])
        else:
            load = result
        if self.nextNode is not None:
            self.nextNode.parameter = load
            print("Node Load", load)
        return load
