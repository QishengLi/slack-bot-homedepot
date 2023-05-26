import json

def save_json_response(json_data, search_term):
    file_path = f"{search_term}.json"
    with open(file_path, "w") as file:
        json.dump(json_data, file)


def check_success_from_json_file(search_term):
    file_path = f"{search_term}.json"
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            success = data["request_info"]["success"]
            return success
    except (IOError, FileNotFoundError) as e:
        print(f"Error: Failed to read JSON file: {str(e)}")
    except KeyError as e:
        print(f"Error: Invalid JSON structure - {str(e)} key not found")
    except Exception as e:
        print(f"Error: {str(e)}")


# Function to get state
def get_state(key, default=None):
    try:
        with open('state.json', 'r') as f:
            state = json.load(f)
        return state.get(key, default)
    except FileNotFoundError:
        # Return the default value if the state file doesn't exist
        return default

# Function to set state
def set_state(key, value):
    try:
        # First load existing state
        with open('state.json', 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        # If there is no existing state, start with an empty state
        state = {}
    # Set the new value for the given key in the state
    state[key] = value
    # Write the updated state back to the file
    with open('state.json', 'w') as f:
        json.dump(state, f)