import queue


class Graph:
    def __init__(self, graph_storage_name):
        graph_storage = open(graph_storage_name, "r")
        self.graph_storage_name = graph_storage_name
        self.adjacency_list = dict()
        self.rules = dict()
        self.graph_storage_size = 0
        for line in graph_storage.readlines():
            type_operation, vertex1, vertex2 = self.__convert_text_to_operation(line)

            if type_operation == "+":
                self.add_edge(vertex1, vertex2, save_operation=False)
            else:
                self.erase_edge(vertex1, vertex2, save_operation=False)
            self.graph_storage_size += 1

    def __check_rule(self, vertex, text):
        rule = self.rules[vertex]
        return len(text) >= len(rule) and text[:len(rule)] == rule

    def __convert_text_to_operation(self, text):
        text = text.split()
        return text[0], (int(text[1]), text[2]), (int(text[3]), text[4])

    def __convert_operation_to_text(self, type_operation, vertex1, vertex2):
        return type_operation + " " + str(vertex1[0]) + " " + vertex1[1] + " " + str(vertex2[0]) + " " + vertex2[1] + "\n"

    def __reset_graph_storage(self):
        graph_storage = open(self.graph_storage_name, "w")
        self.graph_storage_size = 0
        for vertex1 in self.adjacency_list:
            for vertex2 in self.adjacency_list[vertex1]:
                graph_storage.write(self.__convert_operation_to_text("+", vertex1, vertex2))
                self.graph_storage_size += 1
        graph_storage.close()

    def __add_operation_to_storage(self, type_operation, vertex1, vertex2):
        graph_storage = open(self.graph_storage_name, "a")
        graph_storage.write(self.__convert_operation_to_text(type_operation, vertex1, vertex2))
        graph_storage.close()

        self.graph_storage_size += 1
        if self.graph_storage_size >= 2 * len(self.adjacency_list) ** 2:
            self.__reset_graph_storage()

    def get_reachable_vertices(self, vertex_start, text):
        used = set()
        used.add(vertex_start)
        q = queue.Queue()
        q.put(vertex_start)
        while not q.empty():
            v = q.get()
            if not self.__check_rule(v, text):
                continue

            for to in self.adjacency_list[v]:
                if to in used:
                    continue

                used.add(to)
                q.put(to)

        used.discard(vertex_start)
        return list(used)

    def add_vertex(self, vertex):
        if not (vertex in self.adjacency_list):
            self.rules[vertex] = ""
            self.adjacency_list[vertex] = set()

    def set_rule(self, id, rule):
        vertex = (int(id[:-2]), id[-2:])
        self.add_vertex(vertex)
        self.rules[vertex] = rule

    def add_edge(self, vertex1, vertex2, save_operation=True):
        self.add_vertex(vertex1)
        self.add_vertex(vertex2)
        self.adjacency_list[vertex1].add(vertex2)
        if save_operation:
            self.__add_operation_to_storage("+", vertex1, vertex2)

    def erase_edge(self, vertex1, vertex2, save_operation=True):
        if vertex1 in self.adjacency_list:
            self.adjacency_list[vertex1].discard(vertex2)
        if vertex2 in self.adjacency_list:
            self.adjacency_list[vertex2].discard(vertex1)
        if save_operation:
            self.__add_operation_to_storage("-", vertex1, vertex2)
