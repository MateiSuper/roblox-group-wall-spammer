import requests
import pytesseract
from PIL import Image
from io import BytesIO
import time
import json

with open('config.json', 'r') as file:
    config = json.load(file)

print("""

██╗░░░██╗██╗░░░██╗██╗░░░██╗███████╗
╚██╗░██╔╝╚██╗░██╔╝╚██╗░██╔╝╚════██║
░╚████╔╝░░╚████╔╝░░╚████╔╝░░░░░██╔╝
░░╚██╔╝░░░░╚██╔╝░░░░╚██╔╝░░░░░██╔╝░
░░░██║░░░░░░██║░░░░░░██║░░░░░██╔╝░░
░░░╚═╝░░░░░░╚═╝░░░░░░╚═╝░░░░░╚═╝░░░
""")

# Configuration
message = config['message']
cookies_file = config['cookies_file']
groups_file = config['groups_file']
captcha_url = config['captcha_url']
group_wall_url_template = config['group_wall_url_template']

def load_cookies(file_path):
    cookies = {}
    with open(file_path, 'r') as file:
        for line in file:
            if not line.strip():
                continue
            name, value = line.strip().split('=', 1)
            cookies[name] = value
    return cookies

def load_groups(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def solve_captcha(session, captcha_url):
    response = session.get(captcha_url)
    img = Image.open(BytesIO(response.content))
    captcha_text = pytesseract.image_to_string(img)
    return captcha_text.strip()

def post_message(session, group_wall_url, group_id, message, captcha_text):
    post_data = {
        'body': message,
        'captchaToken': captcha_text
    }
    headers = {
        'Content-Type': 'application/json',
        'X-CSRF-TOKEN': session.cookies.get('X-CSRF-TOKEN')
    }
    response = session.post(group_wall_url.format(group_id=group_id), json=post_data, headers=headers)
    return response.status_code, response.json()

if __name__ == "__main__":
    cookies = load_cookies(cookies_file)
    group_ids = load_groups(groups_file)

    session = requests.Session()
    session.cookies.update(cookies)

    message_count = 0

    for group_id in group_ids:
        captcha_solved = False
        while not captcha_solved:
            captcha_text = solve_captcha(session, captcha_url)
            print(f"Captcha solved: {captcha_text}")
            if captcha_text:
                captcha_solved = True
                status_code, response_json = post_message(session, group_wall_url_template, group_id, message, captcha_text)
                if status_code == 200:
                    print(f"Message posted successfully to group {group_id}")
                    message_count += 1
                    if message_count >= 3:
                        print("Three messages sent. Exiting.")
                        break
                else:
                    print(f"Failed to post the message to group {group_id}. Retrying...")
                    if 'X-RateLimit-Remaining' in response_json:
                        print("Rate limit detected, waiting for 10 seconds...")
                        time.sleep(10)
            else:
                print("Failed to solve CAPTCHA. Retrying...")
        if message_count >= 3:
            break
