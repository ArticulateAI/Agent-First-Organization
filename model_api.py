import os
import logging
from typing import Dict
import json
from http import HTTPStatus
import argparse
import uvicorn

from openai import OpenAI
from fastapi import FastAPI, Response

from arklex.env.env import Env
from arklex.orchestrator.orchestrator import AgentOrg
from arklex.utils.model_config import MODEL


logger = logging.getLogger(__name__)
app = FastAPI()


def get_api_bot_response(args, history, user_text, parameters, env):
    data = {"text": user_text, 'chat_history': history, 'parameters': parameters}
    orchestrator = AgentOrg(config=os.path.join(args.input_dir, "taskgraph.json"), env=env)
    result = orchestrator.get_response(data)

    return result['answer'], result['parameters']


@app.post("/eval/chat")
def predict(data: Dict):
    history = data['history']
    params = data['parameters']
    workers = data['workers']
    tools = data['tools']
    user_text = history[-1]['content']

    env = Env(
        tools = tools,
        workers = workers,
        slotsfillapi = ""
    )
    answer, params = get_api_bot_response(args, history[:-1], user_text, params, env)
    return {"answer": answer, "parameters": params}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start FastAPI with custom config.")
    parser.add_argument('--input-dir', type=str, default="./examples/test")
    parser.add_argument('--model', type=str, default=MODEL["model_type_or_path"])
    parser.add_argument('--port', type=int, default=8000, help="Port to run the FastAPI app")
    
    args = parser.parse_args()
    os.environ["DATA_DIR"] = args.input_dir
    MODEL["model_type_or_path"] = args.model

    #run server
    uvicorn.run(app, host="0.0.0.0", port=args.port)