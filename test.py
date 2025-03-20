import re
import json

def extract_json_from_string(input_string):
    # Regular expression to find JSON code blocks
    pattern = r'```json\n(.*?)\n```'
    match = re.search(pattern, input_string, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            json_obj = json.loads(json_str)
            return json_obj
        except json.JSONDecodeError:
            print("Error: JSON decoding failed.")
            return None
    else:
        print("Error: No JSON code block found.")
        return None

# Example usage
input_string = '''content='```json
{
  "action_id": 4,
  "action_name": "Decelerate",
  "explanation": "The car ahead is traveling slower, and lane changes are unsafe. Decelerating allows the ego car to maintain a safe following distance and avoid a collision."
}
```' additional_kwargs={} response_metadata={'model': 'gemma3:12b', 'created_at': '2025-03-20T08:24:00.096754Z', 'done': True, 'done_reason': 'stop', 'total_duration': 5621021708, 'load_duration': 48204666, 'prompt_eval_count': 721, 'prompt_eval_duration': 2939357167, 'eval_count': 68, 'eval_duration': 2633009458, 'message': Message(role='assistant', content='', images=None, tool_calls=None)} id='run-b77e037c-ca92-433b-9736-73952fbf8091-0' usage_metadata={'input_tokens': 721, 'output_tokens': 68, 'total_tokens': 789}'''

extracted_json = extract_json_from_string(input_string)
if extracted_json:
    print(extracted_json)