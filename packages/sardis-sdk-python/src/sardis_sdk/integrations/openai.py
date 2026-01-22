def get_openai_function_schema():
    """
    Returns the JSON schema for OpenAI Function Calling / Swarm.
    """
    return {
        "name": "sardis_pay",
        "description": "Executes a secure payment using Sardis MPC wallet. Use this when the user needs to buy something or pay for a service.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "The amount to pay in USD."
                },
                "merchant": {
                    "type": "string",
                    "description": "The name of the merchant or service provider."
                },
                "purpose": {
                    "type": "string",
                    "description": "The reason for the payment (e.g. 'API Credits')."
                }
            },
            "required": ["amount", "merchant"]
        }
    }
