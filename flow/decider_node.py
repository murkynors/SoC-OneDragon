from flow import base_node


class DeciderNode(base_node.BaseNode):
    def __init__(self, nodeName, parentNode, nextNode, actionFunction, isRootNode, returnMapper):
        super().__init__(nodeName, parentNode, nextNode, actionFunction, isRootNode)
        self.returnMapper = returnMapper

    def getMappedNextNode(self, input_key):
        return self.returnMapper[input_key]
