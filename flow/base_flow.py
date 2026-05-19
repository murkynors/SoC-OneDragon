from soc_one_dragon.flow.base_node import BaseNode
from soc_one_dragon.flow.decider_node import DeciderNode


class BaseFlow:
    def __init__(self, node: BaseNode):
        self.rootNode = node
        self.FlowHistory = []
        self.NodeList = []
        self.currentNode = self.rootNode
        self.skipTargetNode = None
        self.isSkipping = False

    def traverseFlow(self):
        if not self.rootNode:
            raise ValueError('No root node set for flow')

        self.rootNode.setRootNode(True)
        self.currentNode = self.rootNode
        result = None
        print(
            "#######################",
            "Flow Start Root Node: ",
            self.rootNode.nodeName,
            " | Parameter:  ",
            self.rootNode.parameter,
            "#######################",
        )
        while self.currentNode:
            nextNode = self.currentNode.nextNode
            self.FlowHistory.append(self.currentNode.nodeName)
            if isinstance(self.currentNode, DeciderNode):
                nextNode, result = self._execute_decider_node()
            else:
                result = self.currentNode.executeAction()
                if isinstance(result, dict) and "error" in result:
                    print("Error in node: ", self.currentNode.nodeName, " | Error: ", result["error"])
                    return result
                nextNode, _ = self._apply_skip_if_needed(nextNode)
                print("Next Node" if nextNode else "No Next Node", getattr(nextNode, "nodeName", ""))

            if nextNode:
                self.currentNode = nextNode
            else:
                self.currentNode = None
                return result

    def _execute_decider_node(self):
        decider_node = self.currentNode
        decider_node.executeAction()
        nextNode: BaseNode = decider_node.getMappedNextNode(decider_node.fullRes[1])
        print('Decider NodeMapper Variable: ', decider_node.fullRes[1])
        self.currentNode.nextNode = nextNode

        nextNode, skipped = self._apply_skip_if_needed(nextNode)
        if not skipped:
            # 决策节点的 fullRes[0] 是给选中分支节点继续处理的载荷。
            nextNode.parentNode = self.currentNode
            nextNode.parameter = decider_node.fullRes[0]
        print('Decider Next Node: ', nextNode.nodeName)
        return nextNode, decider_node.fullRes

    def _apply_skip_if_needed(self, nextNode):
        if self.isSkipping:
            self.isSkipping = False
            nextNode = self.skipTargetNode
            self.skipTargetNode = None
            if nextNode:
                print('Decider Node Skipping to: ', nextNode.nodeName)
            return nextNode, True
        return nextNode, False

    def appendToNodeList(self, node: BaseNode):
        self.NodeList.append(node)

    def executeFlow(self, inputVar=None):
        if inputVar is not None:
            self.rootNode.parameter = inputVar
        res = self.traverseFlow()
        return res

    def skipToNode(self, nodeName, parameter=None):
        for node in self.NodeList:
            if node.nodeName == nodeName:

                if parameter is not None:
                    node.parameter = parameter
                else:
                    node.parameter = self.currentNode.parameter
                self.skipTargetNode = node
                self.isSkipping = True
                break
        return self.currentNode
