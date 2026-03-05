import re

def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        extracted_string = match.group(1)   # use group(1), not group(0)
        return extracted_string
    return ""

def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])
    return result

if __name__ == "__main__":   # ✅ double equal signs here
    print(get_str_from_food_dict({"pizza": 2, "samosa": 1}))
  #  print(extract_session_id("projects/angel-chatbot-for-food-de-tirf/agent/sessions/36d4adb3-f98f-ae02-2520-0d2bc2cc5178/contexts/ongoing-order"))
