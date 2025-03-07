import json
import random
from arklex.evaluation.get_documents import load_docs
from arklex.evaluation.build_user_profiles import build_profile, ATTR_TO_PROFILE
from arklex.evaluation.chatgpt_utils import (chatgpt_chatbot, query_chatbot, filter_convo, adjust_goal,
                                               flip_hist, generate_goals, format_chat_history_str, flip_hist_content_only)

# USER_DATA_KEYS = ['goal', 'product_experience_level', 'deal_stage', 'customer_type', 'decision_making_authority', 'persona', 'discovery_type', 'buying_behavior']
USER_DATA_KEYS = ['goal', 'product_experience_level', 'customer_type', 'persona', 'discovery_type', 'buying_behavior']

def get_relevant_vals(attr):
    vals = []
    for key in USER_DATA_KEYS:
        vals.append(attr[key])
    return vals

def count_matches(l1,l2):
    num_matches = 0
    for i in range((len(l1))):
        if l1[i] == l2[i]:
            num_matches += 1
    return num_matches

def join_messages(messages):
    message_str = ""
    for message in messages:
        if message['role'] == 'bot_follow_up':
            continue
        message_str += f"{message['role']}: {message['content']}\n"
    return message_str[:-1]

def create_convo_profile(best_match, attr_vals, summary):
    dict_profile = {}
    for i in range(len(USER_DATA_KEYS)):
        if best_match[i] == 'other':
            continue
        dict_profile[USER_DATA_KEYS[i]] = best_match[i]
    
    text_profile = ''
    for key, value in dict_profile.items():
        text_profile += f"{key}: {value}\n"
    profile = chatgpt_chatbot([{'role': 'user', 'content': ATTR_TO_PROFILE.format(company_summary=summary, user_attr=text_profile[:-1])}])
    return profile

def retrieve_convo(attr_vals, all_profiles, user_convos, summary):
    split_profiles = [p.split(',') for p in all_profiles]
    best_match = None
    max_matches = 0
    for profile in split_profiles:
        num_matches = count_matches(attr_vals, profile)
        if num_matches >= max_matches:
            best_match = profile
            max_matches = num_matches
            num_matches = 0

    convo = random.choice(user_convos[','.join(best_match)])
    convo_messages = join_messages(convo['message'])
    convo_profile = create_convo_profile(best_match, attr_vals, summary)
    return convo_messages, convo_profile

def get_example_convo(attr, synthetic_data_params, summary):
    with open(synthetic_data_params['data_file']) as f:
        user_convos = json.load(f)

    all_profiles = list(user_convos.keys())
    attr_vals = get_relevant_vals(attr)
    convo, matching_profile = retrieve_convo(attr_vals, all_profiles, user_convos, summary)
    return convo, matching_profile

def retrieve_prompts(profile, goal, attr, summary, synthetic_data_params):
    if synthetic_data_params['data_file'] is None:
        instructional_prompt = f'Pretend you are a human interacting with a customer service chatbot for the following company: {summary}\nYou have the following goal when interacting with this chatbot:\n{goal}\nHere is a description of the customer you are pretending to be:\n{profile}\nHave a conversation with the chatbot while trying to achieve your goal as this customer. Make sure the conversation is natural. For example, if the chatbot asks you a question you should answer it.'
        start_text = "Humans write short questions with occasional typos. Here are some examples of what a human customer would type: [how much is it?, Can you send info to my email, yes I need a job, want to check both proposals to rent and buy, How much does it cost a [PRODUCT_HERE], Im interested in [PRODUCT_HERE], hi i would like to rent out [PRODUCT_HERE] but im wondering which countries are available for rental]. Replicate the writing behavior of a human customer and begin the conversation with a question to achieve your goal."
    else:
        example_convo, matching_profile = get_example_convo(attr, synthetic_data_params, summary)
        instructional_prompt = f'Pretend you are a human interacting with a customer service chatbot for the following company: {summary}\nYou have the following goal when interacting with this chatbot:\n{goal}\nHere is a description of the customer you are pretending to be:\n{profile}\nHave a conversation with the chatbot while trying to achieve your goal as this customer. Make sure the conversation is natural. For example, if the chatbot asks you a question you should answer it. Below is an example conversation between a user with a similar profile to yours that you can use a guide. However, keep in mind that the users profile may not be the exact same as yours, so take that into consideration when conducting the conversation. Here is the sample users profile:\n{matching_profile}\nAnd here is the conversation between this user and the chatbot:\n{example_convo}'
        start_text = "Replicate the writing behavior of a human customer and begin the conversation with a question to achieve your goal."
    return instructional_prompt, start_text

def check_goal_completion(goal, convo):
    convo_str = format_chat_history_str(flip_hist_content_only(convo[2:]))
    prompt = f"Here is a conversation between a user and a customer service chatbot assistant:\n{convo_str}\n\nThe user's goal is the following: {goal}\nOutput False if the user needs to learn more information regarding their goal. Output True otherwise. Only onput True or False and nothing else."
    output = chatgpt_chatbot([{'role': 'user', 'content': prompt}])
    return output == "True"

def conversation(model_api, profile, goal, attr, summary, model_params, synthetic_data_params, env_config):
    instructional_prompt, start_text = retrieve_prompts(profile, goal, attr, summary, synthetic_data_params)
    history = []
    history.append({'role': 'system','content': instructional_prompt})
    history.append({'role': 'user', 'content': start_text})
    chatbot_history = []
    model_params = {}
    goal_completetion = False

    for i in range(synthetic_data_params['max_turns']):
        output = chatgpt_chatbot(history) 
        history.append({'role': 'assistant', 'content': output})
        chatbot_history.append({'role': 'assistant', 'content': output})
        curr_node = model_params.get('curr_node', "start") 
        response_data = query_chatbot(model_api, chatbot_history, model_params, env_config)
        answer = response_data["answer"]
        answer = answer.replace('\n', ' ')
        model_params = response_data["parameters"]
        metadata = model_params["metadata"]
        pred_intent = response_data['parameters']['nlu_records'][-1]['pred_intent']
        history[-1]['intent'] = pred_intent
        history[-1]['curr_node'] = curr_node
        history[-1]['metadata'] = metadata

        history.append({'role': 'user', 'content': answer})
        chatbot_history.append({'role': 'user', 'content': answer})
        if i > 2 and check_goal_completion(goal, history.copy()):
            goal_completetion = True
            # history.append({'goal_completetion': True})
            break
    
    # if not history[-1].get('goal_completetion', False):
    #     history.append({'goal_completetion': False})
    return history, goal_completetion

def generate_conversations(model_api, profiles, goals, attributes_list, summary, model_params, synthetic_data_params, env_config):
    convos = []
    for profile, goal, attr in zip(profiles, goals, attributes_list):
        convo, goal_completion = conversation(model_api, profile, goal, attr, summary, model_params, synthetic_data_params, env_config)
        syn_convo = flip_hist(filter_convo(convo, filter_turns=False))
        convos.append(
            {
                "convo": syn_convo,
                "profile": profile,
                "goal": goal,
                "attributes": attr,
                "goal_completion": goal_completion
            }
        )
    return convos

def simulate_conversations(model_api, model_params, synthetic_data_params, config):
    profiles, goals, attributes_list = build_profile(synthetic_data_params, config)
    summary = config['intro']
    env_config = {
        "workers": config['workers'],
        "tools": config["tools"]
    }
    
    # try:
    conversations = generate_conversations(
        model_api,
        profiles,
        goals,
        attributes_list,
        summary,
        model_params,
        synthetic_data_params,
        env_config,
    )
    # except Exception as e:
    #     print("Generate conversations failed")
    #     print("Error: ", e)
    #     conversations = []
    return conversations, goals

if __name__ == "__main__":
    model_api = "http://adaptation.cs.columbia.edu:55231/qa/richtech/v1alpha1"
    synthetic_data_params = {'num_convos': 5, 'num_goals': 3, 'max_turns': 10}
    model_params = {}
    convos  = simulate_conversations(model_api, model_params, synthetic_data_params)
    with open('p1_sample_convos.json', 'w') as f:
        json.dump(convos, f, indent=5)