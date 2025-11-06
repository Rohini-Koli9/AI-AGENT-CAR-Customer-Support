import uuid
from core import *

# Let's create an example conversation a user might have with the assistant


# Update with the backup file so we can restart from the original place in each section



user_id_file_path = os.getenv('USER_ID_FILE')

# Default user info
user_name = "Guest"

if user_id_file_path and os.path.exists(user_id_file_path):
    with open(user_id_file_path, 'r') as file:
        user_id = file.read().strip()
else:
    user_id = 101

thread_id = str(uuid.uuid4())
user_info = customers_df[customers_df['user_id'] == int(user_id)]
user_info = user_info.to_dict(orient='records')[0]
config = {
    "configurable": {
        "user_info": user_info,
        # Checkpoints are accessed by thread_id
        "thread_id": thread_id,
    }
}
print(thread_id)
print(user_info)

chat_history = []
def chatloop(prompt):
    _printed = set()  # Track printed message IDs
    retry_count = 0  # Initialize retry counter
    max_retries = 2  # Maximum number of retries before exiting

    while retry_count < max_retries:

        try:
            all_msg = part_1_graph.invoke(
                {"messages": ("user", prompt)}, config
            )
            msg = all_msg.get('messages')[-1]
            
            # Check if msg is a string (error case)
            if isinstance(msg, str):
                print(f"Received string response: {msg}")
                return msg
            
            # Get the message content
            clean_message = msg.content if hasattr(msg, 'content') else str(msg)
            
            # Check for error indicators but don't retry for normal messages
            if "having trouble processing" in clean_message.lower():
                print(f"An error has occurred: {clean_message}.")
                retry_count += 1  # Increment retry counter
                prompt = "Please help me with my request."
                continue  # Retry the chat loop with the same prompt

            print(clean_message)
            try:
                if hasattr(msg, 'response_metadata'):
                    print(msg.response_metadata.get('token_usage', {}).get('total_tokens', 'N/A'))
            except Exception:
                pass

            return str(clean_message)  # Return only the cleaned response

        except Exception as e:
            print(f"Exception in chatloop: {e}")
            retry_count += 1  # Increment retry counter
            if retry_count < max_retries:
                prompt = "Please help me with my previous request."
                continue
            else:
                break


    return "Can you clarify your request please!"
