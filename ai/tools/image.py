import os
import base64
from ai.agent import Agent


def analyze_image(filename: str, agent_model: str = None) -> str:
    """
    Tool function: Reads a local image file and uses an LLM to describe its content.

    Args:
        filename (str): The path to the image file.
        agent_model (str, optional): The model to use for analysis. Defaults to None.

    Returns:
        str: The description of the image from the LLM.
    """
    if not os.path.exists(filename):
        return f"Error: File '{filename}' not found for description."

    try:
        with open(filename, "rb") as image_file:
            image_bytes = image_file.read()

        agent = Agent()
        description = analyze_image_bytes(agent, image_bytes, agent_model=agent_model)
        return f"Description of '{filename}':\n{description}"

    except IOError as e:
        return f"Error reading image file '{filename}': {e}"
    except Exception as e:
        return f"An unexpected error occurred during image description: {e}"


def analyze_image_bytes(agent, image_bytes, agent_model: str = None):
    """Helper function: Sends image bytes to LLM for description using the Agent."""
    if not agent or not hasattr(agent, 'client') or not agent.client:
        return "Image analysis unavailable (ai not initialized)."

    encoded_image = base64.b64encode(image_bytes).decode('utf-8')

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail. If there is any text, transcribe it exactly."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{encoded_image}"
                    },
                },
            ],
        }
    ]

    model_to_use = agent_model if agent_model else "openai/gpt-4o"

    try:
        print(f"--- Analyzing image with model: {model_to_use} ---")
        response = agent.client.chat.completions.create(
            model=model_to_use,
            messages=messages
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error analyzing image: {str(e)}"
