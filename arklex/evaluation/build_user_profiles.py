import json
import random
from arklex.evaluation.get_documents import load_docs
from arklex.evaluation.chatgpt_utils import (chatgpt_chatbot, query_chatbot, filter_convo, adjust_goal,
                                               flip_hist, generate_goals, format_chat_history_str, flip_hist_content_only)

ADDITIONAL_ATTRIBUTES = ['budget', 'purchase_history', 'location']
B2B_ATTRIBUTES = ['job_information', 'business_type', 'company_size']
B2C_ATTRIBUTES = []
ATTR_TO_PROFILE = "Convert the following list user attributes in to a text description of a customer profile for the following company:\n{company_summary}\nThe user attributes are here:\n{user_attr}"

ADAPT_GOAL = "Assume you are planning to speak to a chatbot with the following goal in mind:\n{goal}\nUsing the company information below, re-write this goal into one that is more specific to the company. The new goal should mention specific products (if relevant) or other details about the company. Here is a summary of the company:\n{company_summary}\nHere is a page from the company website:\n{company_doc}"
ADD_ATTRIBUTES = "Your job is to add attributes to a customer profile. Here is an example of an existing profile with the categories on the left and the attributes on the right:\n{user_profile}\nSuggest three attributes for the following category:\n{category}\nThese attributes should be specific values that are relevant to the category and apply to potential customers of the company. You should return a comma separated list of attributes without any descriptions of the attributes. Generated the attributes based on a summary of the company and the company webpage and what kind of customers the compnay is likely targeting. Here is the summary fo the company:\n{company_summary}\nHere is the webpage:\n{company_doc}"


def build_profile(synthetic_data_params, config):
    documents = load_docs(config['documents_dir'], config, synthetic_data_params['num_goals'] * 2)
    attributes_list = filter_attributes(config)
    attributes_list = augment_attributes(attributes_list, config, documents)
    attributes_list = select_attributes(attributes_list, synthetic_data_params)
    attributes_list_with_goals = adapt_goals(attributes_list, config, documents)
    profiles, goals = convert_attributes_to_profiles(attributes_list_with_goals, config)
    return profiles, goals, attributes_list

def filter_attributes(config):
    filtered_attributes = {}
    for key in config['user_attributes'].keys():
        if key == 'generic' or key == config['synthetic_data_params']['customer_type']:
            for subkey in config['user_attributes'][key].keys():
                filtered_attributes[subkey] = config['user_attributes'][key][subkey]
    return filtered_attributes

def select_attributes(user_attributes, synthetic_data_params):
    user_list = []
    for i in range(synthetic_data_params['num_convos']):
        attributes = {}
        for key, value in user_attributes.items():
            attributes[key] = random.choice(value)
        user_list.append(attributes.copy())
    return user_list

def augment_attributes(attributes_list, config, documents):
    # adapt goals using docs and add new attributes from ADDITIONAL_ATTRIBUTES
    # goals = [adapt_goal(goal, config, documents) for goal in attributes_list['goal']]
    new_attrs = generate_attributes(attributes_list, config, documents)
    # attributes_list['goal'] = goals
    attributes_list.update(new_attrs)
    return attributes_list

def adapt_goals(attributes_list, config, documents):
    attributes_list_with_goals = []
    for item in attributes_list:
        new_goal = adapt_goal(item['goal'], config, documents)
        new_item = {}
        for key in item.keys():
            if key == 'goal':
                new_item['goal'] = new_goal
            else:
                new_item[key] = item[key]
        attributes_list_with_goals.append(new_item)
    return attributes_list_with_goals

def adapt_goal(goal, config, documents):
    new_goal = chatgpt_chatbot([{'role': 'user', 'content': ADAPT_GOAL.format(goal=goal, company_summary=config['intro'], company_doc=random.choice(documents))}])
    return new_goal

def generate_attributes(attributes, config, documents):
    text_attribute = ''
    for key, value in attributes.items():
        text_attribute += f"{key}: {value}\n"
    
    all_attributes = ADDITIONAL_ATTRIBUTES
    if config['synthetic_data_params']['customer_type'] == 'b2b':
        all_attributes += B2B_ATTRIBUTES
    elif config['synthetic_data_params']['customer_type'] == 'b2c':
        all_attributes += B2C_ATTRIBUTES

    new_attrs = {}
    for category in all_attributes:
        attrs = chatgpt_chatbot([{'role': 'user', 'content': ADD_ATTRIBUTES.format(user_profile=text_attribute, category=category, company_summary=config['intro'], company_doc=random.choice(documents))}])
        new_attrs[category] = attrs.split(', ')
        # print(attrs.split(', '))
    return new_attrs

def attributes_to_text(attribute_list):
    text_attributes = []
    for item in attribute_list:
        text_attribute = ''
        for key, value in item.items():
            text_attribute += f"{key}: {value}\n"
        text_attributes.append(text_attribute[:-1])
    return text_attributes

def convert_attributes_to_profiles(updated_attributes_list, config):
    profile_list = []
    text_attributes = attributes_to_text(updated_attributes_list)
    for i, attribute in enumerate(text_attributes):
        profile = chatgpt_chatbot([{'role': 'user', 'content': ATTR_TO_PROFILE.format(company_summary=config['intro'], user_attr=attribute)}])
        profile_list.append({"profile": profile, "goal": updated_attributes_list[i]["goal"]})
    
    profiles = [item['profile'] for item in profile_list]
    goals = [item['goal'] for item in profile_list]
    return profiles, goals