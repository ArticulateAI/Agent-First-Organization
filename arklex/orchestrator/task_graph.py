import copy
import logging
import collections

import networkx as nx
import numpy as np
from langchain_openai import ChatOpenAI


from arklex.utils.model_provider_config import PROVIDER_MAP
from arklex.utils.utils import normalize, str_similarity, format_chat_history
from arklex.utils.graph_state import StatusEnum
from arklex.orchestrator.NLU.nlu import NLU, SlotFilling
from arklex.utils.model_config import MODEL

logger = logging.getLogger(__name__)

class TaskGraphBase:
    def __init__(self, name, product_kwargs):
        self.graph = nx.DiGraph(name=name)
        self.product_kwargs = product_kwargs
        self.create_graph()
        self.intents = self.get_pred_intents() # global intents
        self.start_node = self.get_start_node()

    def create_graph(self):
        raise NotImplementedError

    def get_pred_intents(self):
        intents = collections.defaultdict(list)
        for edge in self.graph.edges.data():
            if edge[2].get("attribute", {}).get("pred", False):
                edge_info = copy.deepcopy(edge[2])
                edge_info["source_node"] = edge[0]
                edge_info["target_node"] = edge[1]
                intents[edge[2].get("intent")].append(edge_info)
        return intents
    
    def get_start_node(self):
        for node in self.graph.nodes.data():
            if node[1].get("type", "") == "start":
                return node[0]
        return None


class TaskGraph(TaskGraphBase):
    def __init__(self, name: str, product_kwargs: dict):
        super().__init__(name, product_kwargs)
        self.unsure_intent = {
                "intent": "others",
                "source_node": None,
                "target_node": None,
                "attribute": {
                    "weight": 1,
                    "pred": False,
                    "definition": "",
                    "sample_utterances": []
                }
            }
        self.initial_node = self.get_initial_flow()
        self.model = PROVIDER_MAP.get(MODEL['llm_provider'], ChatOpenAI)(
            model=MODEL["model_type_or_path"], timeout=30000
        )
        self.nluapi = NLU(self.product_kwargs.get("nluapi"))
        self.slotfillapi = SlotFilling(self.product_kwargs.get("slotfillapi"))

    def create_graph(self):
        nodes = self.product_kwargs["nodes"]
        edges = self.product_kwargs["edges"]
        # convert the intent into lowercase
        for edge in edges:
            edge[2]['intent'] = edge[2]['intent'].lower()
        self.graph.add_nodes_from(nodes)
        self.graph.add_edges_from(edges)

    def get_initial_flow(self):
        services_nodes = self.product_kwargs.get("services_nodes", None)
        node = None
        if services_nodes:
            candidates_nodes = [v for k, v in services_nodes.items()]
            candidates_nodes_weights = [list(self.graph.in_edges(n, data="attribute"))[0][2]["weight"] for n in candidates_nodes]
            node = np.random.choice(candidates_nodes, p=normalize(candidates_nodes_weights))
        return node

    def jump_to_node(self, pred_intent, intent_idx, available_nodes, curr_node):
        logger.info(f"pred_intent in jump_to_node is {pred_intent}")
        try:
            candidates_nodes = [self.intents[pred_intent][intent_idx]]
            candidates_nodes = [node for node in candidates_nodes if available_nodes[node["target_node"]]["limit"] >= 1]
            candidates_nodes_weights = [node["attribute"]["weight"] for node in candidates_nodes]
            if candidates_nodes:
                next_node = np.random.choice([node["target_node"] for node in candidates_nodes], p=normalize(candidates_nodes_weights))
                next_intent = pred_intent
            else:  # This is for protection, logically shouldn't enter this branch
                next_node = curr_node
                next_intent = list(self.graph.in_edges(curr_node, data="intent"))[0][2]
        except Exception as e:
            logger.error(f"Error in jump_to_node: {e}")
            next_node = curr_node
            next_intent = list(self.graph.in_edges(curr_node, data="intent"))[0][2]
        return next_node, next_intent
    
    def move_to_node(self, curr_node, available_nodes):
        # if not match other intent, randomly choose one sample from candidate samples
        candidate_samples = []
        candidates_nodes_weights = []
        for out_edge in self.graph.out_edges(curr_node, data=True):
            if out_edge[2]["intent"] == "none" and available_nodes[out_edge[1]]["limit"] >= 1:
                candidate_samples.append(out_edge[1])
                candidates_nodes_weights.append(out_edge[2]["attribute"]["weight"])
        if candidate_samples:
            # randomly choose one sample from candidate samples
            next_node = np.random.choice(candidate_samples, p=normalize(candidates_nodes_weights))
        else:  # leaf node
            next_node = curr_node

        return next_node
    
    def _check_skip(self, node_info):
        task_desp = node_info["attribute"]["task"]
        skip = False
        sys_prompt = """Given the conversation history and the proposed worker, you job is to decide whether the user has already provided the answer for the following task or assistant already did that task before. Reply with 'yes' if user already answered or assistant already did, otherwise 'no'.
        
        Conversation history:
        {chat_history_str}
        Task: 
        {task_desp}
        
        Answer:
        """
        system_prompt = sys_prompt.format(
            chat_history_str=self.chat_history_str, 
            task_desp=task_desp
        )
        skip_status = self.model.invoke(system_prompt)
        logger.debug(f"skip_status: {skip_status}")
        if "yes" in skip_status.content.lower():
            skip = True
        return skip
    
    def _get_node(self, sample_node, available_nodes, available_intents, params, intent=None):
        logger.info(f"available_intents in _get_node: {available_intents}")
        logger.info(f"intent in _get_node: {intent}")
        candidates_intents = collections.defaultdict(list)
        node_info = self.graph.nodes[sample_node]
        node_name = node_info["resource"]["name"]
        id = node_info["resource"]["id"]
        available_nodes[sample_node]["limit"] -= 1
        if intent and available_nodes[sample_node]["limit"] <= 0 and intent in available_intents:
            # delete the corresponding node item from the intent list
            for item in available_intents[intent]:
                if item["target_node"] == sample_node:
                    available_intents[intent].remove(item)
            if not available_intents[intent]:
                available_intents.pop(intent)
        params["curr_node"] = sample_node
        params["available_nodes"] = available_nodes
        params["available_intents"] = available_intents
        # This will be used to check whether we skip the worker or not, which is handled by the task graph framework
        skip = self._check_skip(node_info)
        if skip: # continue check the candidate intents under this node
            node_info = {"id": None, "name": None, "attribute": None}
            for u, v, data in self.graph.out_edges(sample_node, data=True):
                intent = data.get("intent")
                if intent != "none" and data.get("intent") and available_nodes[v]["limit"] >= 1:
                    edge_info = copy.deepcopy(data)
                    edge_info["source_node"] = u
                    edge_info["target_node"] = v
                    candidates_intents[intent].append(edge_info)
        else: # return the node info
            node_info = {"id": id, "name": node_name, "attribute": node_info["attribute"]}
        
        return node_info, params, candidates_intents

    def _postprocess_intent(self, pred_intent, available_intents):
        found_pred_in_avil = False
        real_intent = pred_intent
        idx = 0
        # check whether there are __<{idx}> in the pred_intent
        if "__<" in pred_intent:
            real_intent = pred_intent.split("__<")[0]
        # get the idx
            idx = int(pred_intent.split("__<")[1].split(">")[0])
        for item in available_intents:
            if str_similarity(real_intent, item) > 0.9:
                found_pred_in_avil = True
                real_intent = item
                break
        return found_pred_in_avil, real_intent, idx
    
    # If the local intent is None, determine whether current global intent is finished
    def _switch_pred_intent(self, curr_pred_intent, avail_pred_intents):
        if not curr_pred_intent:
            return True
        other_pred_intents = [intent for intent in avail_pred_intents.keys() if intent != curr_pred_intent and intent != self.unsure_intent.get("intent")]
        logger.info(f"_switch_pred_intent function: curr_pred_intent: {curr_pred_intent}")
        logger.info(f"_switch_pred_intent function: avail_pred_intents: {other_pred_intents}")

        prompt = f"The assistant is currently working on the task: {curr_pred_intent}\nOther available tasks are: {other_pred_intents}\nAccording to the conversation, decide whether the user wants to stop the current task and switch to another one.\nConversation:\n{self.chat_history_str}\nThe response should only be yes or no."
        response = self.model.invoke(prompt)        
        if "no" in response.content.lower():
            return False
        return True
            
    def get_node(self, inputs):
        self.text = inputs["text"]
        self.chat_history_str = inputs["chat_history_str"]
        params = inputs["parameters"]
        nlu_records = []

        # get the current node
        curr_node = params.get("curr_node", None)
        if not curr_node or curr_node not in self.graph.nodes:
            curr_node = self.start_node
            params["curr_node"] = curr_node
        else:
            curr_node = str(curr_node)
        logger.info(f"Intial curr_node: {curr_node}")

        # get the current global intent
        curr_pred_intent = params.get("curr_pred_intent", None)

        # give a initial flow for the most common / important service, in case it miss the highest level intent information, it still have the chance to finally enter this from flow stack
        if self.initial_node:
            flow_stack = params.get("flow", [self.initial_node])
        else:
            flow_stack = params.get("flow", [])

        # available global intents
        available_intents = params.get("available_intents", None)
        if not available_intents:
            available_intents = copy.deepcopy(self.intents)
            if self.unsure_intent.get("intent") not in available_intents.keys():
                available_intents[self.unsure_intent.get("intent")].append(self.unsure_intent)
        logger.info(f"available_intents: {available_intents}")
        
        if not params.get("available_nodes", None):
            available_nodes = {}
            for node in self.graph.nodes.data():
                available_nodes[node[0]] = {"limit": node[1]["limit"]}
            params["available_nodes"] = available_nodes
        else:
            available_nodes = params.get("available_nodes")
        
        if not list(self.graph.successors(curr_node)):  # leaf node
            if flow_stack:  # there is previous unfinished flow
                curr_node = flow_stack.pop()
        
        next_node = curr_node  # initialize next node as curr node
        params["curr_node"] = next_node
        logger.info(f"curr_node: {next_node}")

        # Get local intents of the curr_node
        candidates_intents = collections.defaultdict(list)
        for u, v, data in self.graph.out_edges(curr_node, data=True):
            intent = data.get("intent")
            if intent != "none" and data.get("intent") and available_nodes[v]["limit"] >= 1:
                edge_info = copy.deepcopy(data)
                edge_info["source_node"] = u
                edge_info["target_node"] = v
                candidates_intents[intent].append(edge_info)
        logger.info(f"candidates_intents: {candidates_intents}")
        # whether has checked global intent or not, since 1 turn only need to check global intent for 1 time
        global_intent_checked = False

        if not candidates_intents:  # no local intent under the current node
            logger.info(f"no local intent under the current node")
            # if there is no intents available in the whole graph except unsure_intent
            # Then there is no need to predict the intent
            # Direct move to the next node
            if len(available_intents) == 1 and self.unsure_intent.get("intent") in available_intents.keys():
                pred_intent = self.unsure_intent.get("intent")
            else: # global intent prediction
                # Another checking to make sure the user indeed want to switch the current task
                if not self._switch_pred_intent(curr_pred_intent, available_intents):
                    logger.info(f"User doesn't want to switch the current task: {curr_pred_intent}")
                    pred_intent = self.unsure_intent.get("intent")
                else:
                    logger.info(f"User wants to switch the current task: {curr_pred_intent}")
                    global_intent_checked = True
                    # check other intent
                    # if match other intent, add flow, jump over
                    if self.unsure_intent.get("intent") in available_intents.keys():
                        available_intents_w_unsure = copy.deepcopy(available_intents)
                    else:
                        available_intents_w_unsure = copy.deepcopy(available_intents)
                        available_intents_w_unsure[self.unsure_intent.get("intent")].append(self.unsure_intent)
                    logger.info(f"available_intents_w_unsure: {available_intents_w_unsure}")
                    
                    pred_intent = self.nluapi.execute(self.text, available_intents_w_unsure, self.chat_history_str, params.get("metadata", {}))
                    nlu_records.append({"candidate_intents": available_intents_w_unsure, 
                                        "pred_intent": pred_intent, "no_intent": False, "global_intent": True})
                    params["nlu_records"] = nlu_records
                    found_pred_in_avil, pred_intent, intent_idx = self._postprocess_intent(pred_intent, available_intents)
            if pred_intent.lower() != self.unsure_intent.get("intent") and found_pred_in_avil:  # found global intent
                logger.info(f"Global intent changed from {curr_pred_intent} to {pred_intent}")
                curr_pred_intent = pred_intent
                params["curr_pred_intent"] = curr_pred_intent
                next_node, next_intent = self.jump_to_node(pred_intent, intent_idx, available_nodes, curr_node)
                logger.info(f"curr_node: {next_node}")
                node_info, params, candidates_intents = \
                self._get_node(next_node, available_nodes, available_intents, params, intent=next_intent)
                if next_node != curr_node:
                    flow_stack.append(curr_node)
                    params["flow"] = flow_stack
                if node_info["name"]:
                    return node_info, params
                curr_node = params["curr_node"]
                available_nodes = params["available_nodes"]
            while not candidates_intents:  
                # 1. no global intent found and no local intent found
                # 2. gload intent found but skipped based on the _get_node function
                # Then check whether the current node completed or not
                node_status = params.get("node_status", {})
                status = node_status.get(curr_node, StatusEnum.COMPLETE.value)
                if status == StatusEnum.INCOMPLETE.value:
                    logger.info(f"no local or global intent found, the current node is not complete")
                    node_info = {"id": self.graph.nodes[curr_node]["resource"]["id"], "name": self.graph.nodes[curr_node]["resource"]["name"], "attribute": self.graph.nodes[curr_node]["attribute"]}
                    return node_info, params
                # If completed, then move to the next connected node(s) (randomly choose one of them if there are multiple "None" intent connected)
                logger.info(f"no local or global intent found, move to the next connected node(s)")
                next_node = self.move_to_node(curr_node, available_nodes)
                if next_node == curr_node:  # leaf node
                    break
                
                logger.info(f"curr_node: {next_node}")

                node_info, params, candidates_intents = \
                self._get_node(next_node, available_nodes, available_intents, params)
                if params.get("nlu_records", None):
                    params["nlu_records"][-1]["no_intent"] = True  # move on to the next node
                else: # only others available
                    params["nlu_records"] = [{"candidate_intents": [], "pred_intent": "", "no_intent": True, "global_intent": False}]
                
                if node_info["name"]:
                    return node_info, params

                curr_node = params["curr_node"]
                available_nodes = params["available_nodes"]

        curr_node = params["curr_node"]
        available_nodes = params["available_nodes"]
        next_node = curr_node
        logger.info(f"curr_node: {curr_node}")

        # before local intent prediction, check whether the current node complete or not
        node_status = params.get("node_status", {})
        status = node_status.get(curr_node, StatusEnum.COMPLETE.value)
        if status == StatusEnum.INCOMPLETE.value:
            node_info = {"id": self.graph.nodes[curr_node]["resource"]["id"], "name": self.graph.nodes[curr_node]["resource"]["name"], "attribute": self.graph.nodes[curr_node]["attribute"]}
            return node_info, params

        while candidates_intents:  # local intent prediction
            # there are local intent(s) to chooose from
            logger.info("Finish global condition, start local intent prediction")
            if self.unsure_intent.get("intent") in candidates_intents.keys():
                candidates_intents_w_unsure = copy.deepcopy(candidates_intents)
            else:
                candidates_intents_w_unsure = copy.deepcopy(candidates_intents)
                candidates_intents_w_unsure[self.unsure_intent.get("intent")].append(self.unsure_intent)
            logger.info(f"Check intent under current node: {candidates_intents_w_unsure}")

            pred_intent = self.nluapi.execute(self.text, candidates_intents_w_unsure, self.chat_history_str, params.get("metadata", {}))
            nlu_records.append({"candidate_intents": candidates_intents_w_unsure, 
                                "pred_intent": pred_intent, "no_intent": False, "global_intent": False})
            params["nlu_records"] = nlu_records
            found_pred_in_avil, pred_intent, intent_idx = self._postprocess_intent(pred_intent, candidates_intents)
            logger.info(f"found_pred_in_avil: {found_pred_in_avil}, pred_intent: {pred_intent}")
            if found_pred_in_avil:  # found local intent
                if pred_intent.lower() != self.unsure_intent.get("intent") and pred_intent in available_intents.keys():
                    logger.info(f"Global intent changed from {curr_pred_intent} to {pred_intent}")
                    curr_pred_intent = pred_intent
                    params["curr_pred_intent"] = curr_pred_intent
                for edge in self.graph.out_edges(curr_node, data="intent"):
                    if edge[2] == pred_intent:
                        next_node = edge[1]  # found intent under the current node
                        break
                logger.info(f"curr_node: {next_node}")
                node_info, params, candidates_intents = \
                self._get_node(next_node, available_nodes, available_intents, params, intent=pred_intent)
                if node_info["name"]:
                    return node_info, params
                
                curr_node = params["curr_node"]
                available_nodes = params["available_nodes"]
                while not candidates_intents:  # skip this node from _get_node logic and the local intent is None
                    next_node = self.move_to_node(curr_node, available_nodes)
                    if next_node == curr_node:  # leaf node
                        break
                    logger.info(f"curr_node: {next_node}")

                    node_info, params, candidates_intents = \
                    self._get_node(next_node, available_nodes, available_intents, params)
                    if node_info["name"]:
                        return node_info, params
                    curr_node = params["curr_node"]
                    available_nodes = params["available_nodes"]

            elif not global_intent_checked:  # global intent prediction
                # check other intent (including unsure), if found, current flow end, add flow onto stack; if still unsure, then stay at the curr_node, and response without interactive.
                other_intents = collections.defaultdict(list)
                for key, value in available_intents.items():
                    if key not in candidates_intents and key in self.intents and key != "none":
                        other_intents[key] = value

                if self.unsure_intent.get("intent") in other_intents.keys():
                    other_intents_w_unsure = copy.deepcopy(other_intents)
                else:
                    other_intents_w_unsure = copy.deepcopy(other_intents)
                    other_intents_w_unsure[self.unsure_intent.get("intent")].append(self.unsure_intent)

                logger.info(f"Check other intent: {other_intents}")
                
                pred_intent = self.nluapi.execute(self.text, other_intents_w_unsure, self.chat_history_str, params.get("metadata", {}))
                nlu_records.append({"candidate_intents": other_intents, 
                                    "pred_intent": pred_intent, "no_intent": False, "global_intent": True})
                params["nlu_records"] = nlu_records
                found_pred_in_avil, pred_intent, intent_idx = self._postprocess_intent(pred_intent, other_intents)
                logger.info(f"found_pred_in_avil for global intent: {found_pred_in_avil}, pred_intent: {pred_intent}")
                if found_pred_in_avil:  # found global intent
                    if pred_intent.lower() != self.unsure_intent.get("intent"):  # global intent is not unsure
                        logger.info(f"Global intent changed from {curr_pred_intent} to {pred_intent}")
                        curr_pred_intent = pred_intent
                        params["curr_pred_intent"] = curr_pred_intent
                    next_node, next_intent = self.jump_to_node(pred_intent, intent_idx, available_nodes, curr_node)
                    logger.info(f"curr_node: {next_node}")
                    node_info, params, candidates_intents = \
                    self._get_node(next_node, available_nodes, available_intents, params, intent=next_intent)
                    if next_node != curr_node:
                        flow_stack.append(curr_node)
                        params["flow"] = flow_stack
                    if node_info["name"]:
                        return node_info, params
                    curr_node = params["curr_node"]
                    logger.info(f"curr_node: {curr_node}")
                else:  
                    # If user didn't indicate all the intent of children nodes under the current node, 
                    # then we could randomly choose one of Nones to continue the dialog flow
                    next_node = self.move_to_node(curr_node, available_nodes)
                    if next_node == curr_node:  # leaf node or no other nodes to choose from
                        break
                    logger.info(f"curr_node: {next_node}")

                    node_info, params, candidates_intents = \
                    self._get_node(next_node, available_nodes, available_intents, params)
                    if node_info["name"]:  # It will move to the node that with None as intent
                        return node_info, params
                    # neither local nor global intent found and even for the None intent node, it has been skipped
                    # So we just stay at the curr_node and do the next step at the next turn.
                    # Similar to the following else break.
                    break

            else: # neither local nor global intent found
                break
        # if none of the available intents can represent user's utterance, transfer to the DefaultWorker to let it decide for the next step
        if nlu_records:
            nlu_records[-1]["no_intent"] = True  # no intent found
        else: # didn't do prediction at all for the current turn
            nlu_records.append({"candidate_intents": [], "pred_intent": "", "no_intent": True, "global_intent": False})
        params["nlu_records"] = nlu_records
        params["curr_node"] = curr_node
        node_info = {"id": "DefaultWorker", "name": "DefaultWorker", "attribute": {"value": "", "direct": False}}
        
        return node_info, params

    def postprocess_node(self, node):
        node_info = node[0]
        params = node[1]

        dialog_states = params.get("dialog_states", {})
        # update the dialog states
        if dialog_states.get(node_info["id"]):
            dialog_states = self.slotfillapi.execute(dialog_states.get(node_info["id"]), format_chat_history(params.get("history")), params.get("metadata", {}))
        params["dialog_states"] = dialog_states

        return node_info, params
