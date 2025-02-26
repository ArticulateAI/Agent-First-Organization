from datetime import datetime, timezone

from arklex.env.exceptions import AuthenticationError, DataNotFoundError
from ..tools import register_tool, logger
import hubspot
from hubspot.crm.objects.emails import PublicObjectSearchRequest, ApiException
from hubspot.crm.objects.communications.models import SimplePublicObjectInputForCreate
from hubspot.crm.associations.v4 import AssociationSpec
from arklex.env.tools.hubspot.utils import HUBSPOT_AUTH_ERROR

description = "Find the contacts record by email. If the record is found, the lastmodifieddate of the contact will be updated. If the correspodning record is not found, the function will return an error message."


slots = [
    {
        "name": "email",
        "type": "string",
        "description": "The email of the user, such as 'something@example.com'.",
        "prompt": "Thanks for your interest in our products! Could you please provide your email or phone number?",
        "required": True,
    },
    {
        "name": "chat",
        "type": "string",
        "description": "This occurs when user communicates with the chatbot",
        "prompt": "",
        "required": True,
    }
]
outputs = [
    {
        "name": "contact_information",
        "type": "string",
        "description": "The basic contact information for the existing customer (e.g. id, first_name, last_name, etc.)",
    }
]

USER_NOT_FOUND_ERROR = "error: user not found (not an existing customer)"
errors = [
    HUBSPOT_AUTH_ERROR,
    USER_NOT_FOUND_ERROR
]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def find_contact_by_email(email: str, chat: str, **kwargs) -> str:

    access_token = kwargs.get('access_token')

    if not access_token:
        raise AuthenticationError(HUBSPOT_AUTH_ERROR)

    api_client = hubspot.Client.create(access_token=access_token)
    public_object_search_request = PublicObjectSearchRequest(
        filter_groups=[
            {
                "filters": [
                    {
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }
                ]
            }
        ]
    )

    try:
        contact_search_response = api_client.crm.contacts.search_api.do_search(
            public_object_search_request=public_object_search_request)
        logger.info("Found contact by email: {}".format(email))
        contact_search_response = contact_search_response.to_dict()
        if contact_search_response['total'] == 1:
            contact_id = contact_search_response['results'][0]['id']
            communication_data = SimplePublicObjectInputForCreate(
                properties = {
                    "hs_communication_channel_type": "CUSTOM_CHANNEL_CONVERSATION",
                    "hs_communication_body": chat,
                    "hs_communication_logged_from": "CRM",
                    "hs_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            contact_info_properties = {
                'id': contact_id,
                'email': email,
                'first_name': contact_search_response['results'][0]['properties'].get('firstname'),
                'last_name': contact_search_response['results'][0]['properties'].get('lastname')
            }
            try:
                communication_creation_response = api_client.crm.objects.communications.basic_api.create(communication_data)
                communication_creation_response = communication_creation_response.to_dict()
                communication_id = communication_creation_response['id']
                association_spec = [
                    AssociationSpec(
                        association_category="HUBSPOT_DEFINED",
                        association_type_id=82
                    )
                ]
                try:
                    association_creation_response = api_client.crm.associations.v4.basic_api.create(
                        object_type="contact",
                        object_id=contact_id,
                        to_object_type="communication",
                        to_object_id=communication_id,
                        association_spec=association_spec
                    )
                except ApiException as e:
                    logger.info("Exception when calling AssociationV4: %s\n" % e)
            except ApiException as e:
                logger.info("Exception when calling basic_api: %s\n" % e)
            return str(contact_info_properties)
        else:
            raise DataNotFoundError(USER_NOT_FOUND_ERROR)
    except ApiException as e:
        logger.info("Exception when calling search_api: %s\n" % e)



