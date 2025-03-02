# Config

**Config** files are the simple and recommended way to build your [TaskGraph](./Taskgraph/intro.md). A standard JSON document, the [Generator](Taskgraph/Generation) can create and breakdown the role into a series of tasks and steps which are then matched with the appropriate [Workers](Workers/intro) and connected with the proper tasks to create a TaskGraph. 

Here is the structure for a **Config** JSON file:

* `role (Required)`: The general "role" of the chatbot you want to create. For instance, "customer service assistant", "data analyst", "shopping assistant", etc.
* `user_objective (Required)`: The user's goal that the chatbot wants to achieve. Related to the user experience. Description in third person. For instance, "The customer service assistant helps users with customer service inquiries. It can provide information about products, services, and policies, as well as help users resolve issues and complete transactions."
* `builder_objective (Optional)`: The additional target you want the chatbot to achieve beyond the user's goal. Can contain hidden objectives or subtle objectives which is hidden from the user. Describe in third person. For instance, "The customer service assistant helps to request customer's contact information."
* `domain (Optional)`: The domain that you want to create the chatbot for. For instance, "robotics and automation", "Ecommerce", "Healthcare", etc.
* `intro (Optional)`: The introduction of the above domain that you want to create the chatbot for. It should contain the information about the domain, the products, services, and policies, etc.
* `task_docs (Optional, List[Dict])`: The documents resources for the taskgraph generation to create the chatbot. Each item in the list should contain the following fields:
    * `source (Required)`: The source url that you want the chatbot to refer to
    * `desc (Optional)` : Short description of the source and how it is used
    * `num (Optional)`: The number of websites that you want the chatbot to refer to for the source, defaults to one (only the url page)
* `rag_docs (Optional, List[Dict])`: If you want to use RAGWorker, then here indicates the documents for the RAG component of chatbot when running chatbot. Each item in the list should contain the following fields:
    * `source (Required)`: The source url that you want the chatbot to refer to
    * `desc (Optional)` : Short description of the source and how it is used
    * `num (Optional)`: The number of websites that you want the chatbot to refer to for the source, defaults to one (only the url page)
* `tasks (Optional, List(Dict))`: The pre-defined list of tasks that the chatbot need to handle. If empty, the system will generate the tasks and the steps to complete the tasks based on the role, objective, domain, intro and docs fields. The more information you provide in the fields, the more accurate the tasks and steps will be generated. If you provide the tasks, it should contain the following fields:
    * `task_name (Required, Str)`: The task that the chatbot need to handle
    * `steps (Required, List(Str))`: The steps to complete the task
* `workers (Required, List(WorkerClassName))`: The [Workers](Workers/Workers.md) pre-defined under `agentorg/workers` folder in the codebase that you want to use for the chatbot.

## Examples
#### [Customer Service Bot](./tutorials/customer-service.md)
```json title="customer_service_config.json"
{
    "role": "customer service assistant",
    "user_objective": "The customer service assistant helps users with customer service inquiries. It can provide information about products, services, and policies, as well as help users resolve issues and complete transactions.",
    "builder_objective": "The customer service assistant helps to request customer's contact information.",
    "domain": "robotics and automation",
    "intro": "Richtech Robotics's headquarter is in Las Vegas; the other office is in Austin. Richtech Robotics provide worker robots (ADAM, ARM, ACE), delivery robots (Matradee, Matradee X, Matradee L, Richie), cleaning robots (DUST-E SX, DUST-E MX) and multipurpose robots (skylark). Their products are intended for business purposes, but not for home purpose; the ADAM robot is available for purchase and rental for multiple purposes. This robot bartender makes tea, coffee and cocktails. Richtech Robotics also operate the world's first robot milk tea shop, ClouTea, in Las Vegas (www.cloutea.com), where all milk tea beverages are prepared by the ADAM robot. The delivery time will be one month for the delivery robot, 2 weeks for standard ADAM, and two months for commercial cleaning robot. ",
    "task_docs": {
        "source": "https://www.richtechrobotics.com/",
        "num": 20
    },
    "tasks": [],
    "workers": [
        "RAGWorker",
        "RagMsgWorker",
        "MessageWorker",
        "SearchWorker",
        "DefaultWorker"
    ]
}
```