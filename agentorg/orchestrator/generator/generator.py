import os
import json
import argparse
import logging
from datetime import datetime
from tqdm import tqdm as progress_bar
import subprocess
import pickle
from pathlib import Path
import inspect
import importlib

from langchain.prompts import PromptTemplate
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from textual.app import App, ComposeResult
from textual.widgets import Tree, Label, Input, Button, Static, Log
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets.tree import TreeNode

from agentorg.utils.utils import postprocess_json
from agentorg.orchestrator.generator.prompts import *
from agentorg.utils.loader import Loader


logger = logging.getLogger(__name__)

class InputModal(Screen):
    """A simple input modal for editing or adding tasks/steps."""
    
    def __init__(self, title: str, default: str = "", node=None, callback=None):
        super().__init__()
        self.title = title
        self.default = default
        self.result = default
        self.node = node
        self.callback = callback


    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.title, classes="title"),
            Input(value=self.default, id="input-field"),
            Horizontal(
                Button("Submit", id="submit"),
                Button("Cancel", id="cancel"),
                id="buttons"
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.result = self.query_one("#input-field", Input).value
            # logger.debug(f"InputModal result: {self.result}")
        if self.callback:
            self.callback(self.result, self.node)
        logger.debug(f"InputModal result: {self.result}")
        self.app.pop_screen()  # Close modal


class TaskEditorApp(App):
    """A Textual app to edit tasks and steps in a hierarchical structure."""

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks
        self.task_tree: Tree[str] = None

    def compose(self) -> ComposeResult:
        self.task_tree = Tree("Tasks")
        self.task_tree.root.expand()

        # Populate the tree with tasks and steps
        for task in self.tasks:
            task_node = self.task_tree.root.add(task["task_name"], expand=True)
            for step in task["steps"]:
                task_node.add_leaf(step)

        yield self.task_tree
        yield Label("Click on a task or step to edit it. Press 'a' to add new item, 'd' to delete, 's' to save and exit.")

    def on_mount(self):
        self.task_tree.focus()

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        selected_node = event.node

        def handle_modal_result(result, node):
            if result is not None:  # Check if the user submitted a valid result
                node.set_label(result)  # Update the tree node's label
                self.call_later(self.update_tasks)  # Ensure task sync runs after UI update

        self.push_screen(
            InputModal(
                f"Edit '{selected_node.label}'", 
                default=str(selected_node.label), 
                node=selected_node,
                callback=handle_modal_result
            )
        )

    async def on_key(self, event):
        selected_node = self.task_tree.cursor_node
        if event.key == "a" and selected_node and selected_node.parent is not None:
            await self.action_add_node(selected_node)
        elif event.key == "d" and selected_node and selected_node.parent is not None:
            selected_node.remove()
            await self.update_tasks()
        elif event.key == "s":
            self.exit(self.tasks)

    async def action_add_node(self, node: TreeNode):
        # if the node is a step node
        if node.parent.parent is not None:
            leaf = True
            node = node.parent
            title=f"Add new step under '{node.label.plain}'"
        else:  # if the node is a task node
            if node.is_expanded: # add step
                leaf = True
                node = node
                title=f"Enter new step under '{node.label.plain}'"
            else:
                leaf = False
                node = node.parent
                title=f"Add new task under '{node.label.plain}'"

        def handle_modal_result(result, node):
            if result is not None:  # Check if the user submitted a valid result
                if leaf:
                    node.add_leaf(result)
                else:
                    node.add(result, expand=True)
                self.call_later(self.update_tasks)  # Ensure task sync runs after UI update

        self.push_screen(
            InputModal(
                title, 
                default="",
                node=node,
                callback=handle_modal_result
            )
        )

    def show_input_modal(self, title: str, default: str = "") -> str:
        modal = InputModal(title, default)
        self.push_screen(modal)
        return modal.result

    async def update_tasks(self):
        self.tasks = []
        for task_node in self.task_tree.root.children:
            task_name = task_node.label.plain
            steps = [step.label.plain for step in task_node.children]
            self.tasks.append({"task_name": task_name, "steps": steps})

        log_message = f"Updated Tasks: {self.tasks}"
        logger.debug(log_message)


class Generator:
    def __init__(self, args, config, model, output_dir):
        self.args = args
        self.product_kwargs = json.load(open(config))
        self.role = self.product_kwargs.get("role")
        self.u_objective = self.product_kwargs.get("user_objective")
        self.b_objective = self.product_kwargs.get("builder_objective")
        self.intro = self.product_kwargs.get("intro")
        self.task_docs = self.product_kwargs.get("task_docs") 
        self.rag_docs = self.product_kwargs.get("rag_docs") 
        self.tasks = self.product_kwargs.get("tasks")
        self.workers = self._init_workers(self.product_kwargs.get("workers"))
        self.tools = self._init_tools(self.product_kwargs.get("tools"))
        self.model = model
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.output_dir = output_dir
    
    def _init_tools(self, tools):
        # return dict of valid tools with name and description
        tool_registry = {}
        for tool in tools:
            tool_id = tool["id"]
            name = tool["name"]
            path = tool["path"]
            try: # try to import the tool to check its existance
                filepath = os.path.join("agentorg.env.tools", path)
                module_name = filepath.replace(os.sep, ".").rstrip(".py")
                module = importlib.import_module(module_name)
                func = getattr(module, name)
            except Exception as e:
                logger.error(f"Tool {name} is not registered, error: {e}")
            tool_name = func().name
            tool_desc = func().description
            tool_registry[tool_id] = {
                "name": tool_name,
                "description": tool_desc
            }
        return tool_registry
    
    def _init_workers(self, workers):
        worker_registry = {}
        for worker in workers:
            worker_id = worker["id"]
            name = worker["name"]
            path = worker["path"]
            try: # try to import the worker to check its existance
                filepath = os.path.join("agentorg.env.workers", path)
                module_name = filepath.replace(os.sep, ".").rstrip(".py")
                module = importlib.import_module(module_name)
                func = getattr(module, name)
            except Exception as e:
                logger.error(f"Worker {name} is not registered, error: {e}")
            worker_name = name
            worker_desc = func().description
            worker_registry[worker_id] = {
                "name": worker_name,
                "description": worker_desc,
                "function": func
            }
        return worker_registry
    
    
    def _generate_tasks(self):
        # based on the type and documents
        prompt = PromptTemplate.from_template(generate_tasks_sys_prompt)
        input_prompt = prompt.invoke({"role": self.role, "u_objective": self.u_objective, "intro": self.intro, "docs": self.documents})
        final_chain = self.model | StrOutputParser()
        answer = final_chain.invoke(input_prompt)
        logger.debug(f"Generated tasks with thought: {answer}")
        self.tasks = postprocess_json(answer)

    def _format_tasks(self):
        # TODO: need to use LLM to match the semantics meaning of the tasks
        new_format_tasks = []
        for task_str in self.tasks:
            task = {}
            task['intent'] = task_str
            task['task'] = task_str
            new_format_tasks.append(task)
        self.tasks = new_format_tasks

    def _generate_best_practice(self, task):
        # Best practice detection
        resources = {}
        for worker_id, worker_info in self.workers.items():
            worker_name = worker_info["name"]
            worker_desc = worker_info["description"]
            worker_func = worker_info["function"]
            # Retrieve all methods of the class
            skeleton = {}
            for name, method in inspect.getmembers(worker_func, predicate=inspect.isfunction):
                signature = inspect.signature(method)
                skeleton[name] = str(signature)
            worker_resource = worker_desc + "\n"
            worker_resource += "The class skeleton of the worker is as follow: \n" + "\n".join([f"{name}{parameters}" for name, parameters in skeleton.items()]) + "\n\n"
            logger.debug(f"Code skeleton of the worker: {worker_resource}")
            
            resources[worker_name] = worker_resource
        resources_str = "\n".join([f"{name}\n: {desc}" for name, desc in resources.items()])
        prompt = PromptTemplate.from_template(check_best_practice_sys_prompt)
        input_prompt = prompt.invoke({"task": task["task"], "level": "1", "resources": resources_str})
        final_chain = self.model | StrOutputParser()
        answer = final_chain.invoke(input_prompt)
        logger.info(f"Best practice detection: {answer}")
        answer = postprocess_json(answer)
        
        if not answer or answer["answer"].lower() == "no":
            best_practice = [
                {
                    "step": 1,
                    "task": task["task"]
                }
            ]
            return best_practice
        
        # Best practice suggestion
        prompt = PromptTemplate.from_template(generate_best_practice_sys_prompt)
        input_prompt = prompt.invoke({"role": self.role, "u_objective": self.u_objective, "task": task["task"], "resources": resources_str})
        final_chain = self.model | StrOutputParser()
        answer = final_chain.invoke(input_prompt)
        logger.debug(f"Generated best practice with thought: {answer}")
        return postprocess_json(answer)
    
    def _finetune_best_practice(self, best_practice):
        # embed build's objective
        if not self.b_objective:
            prompt = PromptTemplate.from_template(embed_builder_obj_sys_prompt)
            input_prompt = prompt.invoke({"best_practice": best_practice, "b_objective": self.b_objective})
            final_chain = self.model | StrOutputParser()
            best_practice = postprocess_json(final_chain.invoke(input_prompt))
        # mapping resources to the best practice
        prompt = PromptTemplate.from_template(embed_resources_sys_prompt)
        resources = {}
        resource_id_map = {}
        for worker_id, worker_info in self.workers.items():
            worker_name = worker_info["name"]
            worker_desc = worker_info["description"]
            resources[worker_name] = worker_desc
            resource_id_map[worker_name] = worker_id
        
        for tool_id, tool_info in self.tools.items():
            tool_name = tool_info["name"]
            tool_desc = tool_info["description"]
            resources[tool_name] = tool_desc
            resource_id_map[tool_name] = tool_id
            
        input_prompt = prompt.invoke({"best_practice": best_practice, "resources": resources})
        final_chain = self.model | StrOutputParser()
        answer = final_chain.invoke(input_prompt)
        json_answer = postprocess_json(answer)
        # add resource id
        for i in range(len(json_answer)):
            ans = json_answer[i]
            resource_id = resource_id_map.get(ans["resource"], None)
            if not resource_id:
                logger.info("Error while retrieving resource id")
            json_answer[i]["resource_id"] = resource_id
        return json_answer
    
    def _format_task_graph(self, finetuned_best_practices):
        node_id = 1
        nodes = []
        edges = []
        task_ids = {}
        for best_practice, task in zip(finetuned_best_practices, self.tasks):
            task_ids[node_id] = task
            for idx, step in enumerate(best_practice):
                node = []
                node.append(str(node_id))
                node.append({
                    "resource": {
                        "id": step["resource_id"],
                        "name": step['resource'],
                    },
                    "attribute": {
                        "value": step['example_response'],
                        "task": step['task'],
                        "directed": False
                    },
                    "limit": 1
                })
                nodes.append(node)

                if idx == 0:
                    edge = []
                    edge.append("0")
                    edge.append(str(node_id))
                    edge.append({
                        "intent": task['intent'],
                        "attribute": {
                            "weight": 1,
                            "pred": True,
                            "definition": "",
                            "sample_utterances": []
                        }
                    })
                else:
                    edge = []
                    edge.append(str(node_id - 1))
                    edge.append(str(node_id))
                    edge.append({
                        "intent": "None",
                        "attribute": {
                            "weight": 1,
                            "pred": False,
                            "definition": "",
                            "sample_utterances": []
                        }
                    })
                edges.append(edge)
                node_id += 1
        
        # Add the start node
        start_node = []
        start_node.append("0")
        # generate the start message
        prompt = PromptTemplate.from_template(generate_start_msg)
        input_prompt = prompt.invoke({"role": self.role, "u_objective": self.u_objective})
        final_chain = self.model | StrOutputParser()
        answer = final_chain.invoke(input_prompt)
        start_msg = postprocess_json(answer)
        message_worker_id = None
        for worker_id, worker_info in self.workers.items():
            if worker_info["name"] == "MessageWorker":
                message_worker_id = worker_id
                break
        start_node.append({
            "resource": {
                "id": message_worker_id,
                "name": "MessageWorker",
            },
            "attribute": {
                "value": start_msg['message'],
                "task": "start message",
                "directed": False
            },
            "limit": 1,
            "type": "start"
        })
        nodes.insert(0, start_node)

        task_graph = {
            "nodes": nodes,
            "edges": edges
        }
        for key, value in self.product_kwargs.items():
            task_graph[key] = value

        return task_graph
    
    def _load_docs(self):
        if self.task_docs:
            filepath = os.path.join(self.output_dir, "task_documents.pkl")
            total_num_docs = sum([doc.get("num") if doc.get("num") else 1 for doc in self.task_docs])
            loader = Loader()
            if Path(filepath).exists():
                logger.warning(f"Loading existing documents from {os.path.join(self.output_dir, 'task_documents.pkl')}! If you want to recrawl, please delete the file or specify a new --output-dir when initiate Generator.")
                crawled_urls_full = pickle.load(open(os.path.join(self.output_dir, "task_documents.pkl"), "rb"))
            else:
                crawled_urls_full = []
                for doc in self.task_docs:
                    source = doc.get("source")
                    num_docs = doc.get("num") if doc.get("num") else 1
                    urls = loader.get_all_urls(source, num_docs)
                    crawled_urls = loader.to_crawled_obj(urls)
                    crawled_urls_full.extend(crawled_urls)
                Loader.save(filepath, crawled_urls_full)
            if total_num_docs > 50:
                limit = total_num_docs // 5
            else:
                limit = 10
            crawled_docs = loader.get_candidates_websites(crawled_urls_full, limit)
            logger.debug(f"Loaded {len(crawled_docs)} documents")
            self.documents = "\n\n".join([f"{doc['url']}\n{doc['content']}" for doc in crawled_docs])
        else:
            self.documents = ""


    def generate(self):

        # Step 0: Load the docs
        self._load_docs()
        
        # Step 1: Generate the tasks
        if not self.tasks:
            self._generate_tasks()
            logger.info(f"Generated tasks: {self.tasks}")
        else:
            self._format_tasks()
            logger.info(f"Formatted tasks: {self.tasks}")

        # Step 2: Generate the task planning
        best_practices = []
        for idx, task in progress_bar(enumerate(self.tasks), total=len(self.tasks)):
            logger.info(f"Generating best practice for task {idx}: {task}")
            best_practice = self._generate_best_practice(task)
            logger.info(f"Generated best practice for task {idx}: {best_practice}")
            best_practices.append(best_practice)

        # Step 3: iterate with user
        format_tasks = []
        for best_practice, task in zip(best_practices, self.tasks):
            try:
                task_name = task['task']
                steps = [bp["task"] for bp in best_practice]
            except Exception as e:
                logger.error(f"Error in format task {task}")
                logger.error(e)
                continue
            format_tasks.append({"task_name": task_name, "steps": steps})
        app = TaskEditorApp(format_tasks)
        hitl_result = app.run()
        task_planning_filepath = os.path.join(self.output_dir, f'taskplanning.json')
        json.dump(hitl_result, open(task_planning_filepath, "w"), indent=4)

        # Step 4: Pair task with worker
        finetuned_best_practices = []
        for idx_t, task in enumerate(hitl_result):
            steps = task["steps"]
            format_steps = []
            for idx_s, step in enumerate(steps):
                format_steps.append({
                    "step": idx_s + 1,
                    "task": step
                })
            finetuned_best_practice = self._finetune_best_practice(format_steps)
            logger.info(f"Finetuned best practice for task {idx_t}: {finetuned_best_practice}")
            finetuned_best_practices.append(finetuned_best_practice)

        # Step 5: Format the task graph
        task_graph = self._format_task_graph(finetuned_best_practices)

        # Step 6: Save the task graph
        taskgraph_filepath = os.path.join(self.output_dir, f'taskgraph.json')
        with open(taskgraph_filepath, "w") as f:
            json.dump(task_graph, f, indent=4)

        return taskgraph_filepath
