import gradio as gr
import random
import os
import json
import time
import shared
import modules.config
import fooocus_version
import requests
import modules.html
import modules.async_worker as worker
import modules.constants as constants
import modules.flags as flags
import modules.gradio_hijack as grh
import modules.style_sorter as style_sorter
import modules.meta_parser
import args_manager
import copy
import launch
from extras.inpaint_mask import SAMOptions

from modules.sdxl_styles import legal_style_names
from modules.private_logger import get_current_html_path
from modules.ui_gradio_extensions import reload_javascript
from modules.auth import auth_enabled, check_auth
from modules.util import is_json

FASTAPI_SERVER_URL = "https://6a03-2a02-8109-b526-c500-ad2c-86ae-c6e1-be69.ngrok-free.app/upload/"
PROMPTS_FILE = "prompts.json"
CONFIG_FILE = "config.json"

# Load settings from the configuration file
def load_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

# Load prompts from the prompts file
def load_prompts(prompts_path):
    with open(prompts_path, 'r') as f:
        return json.load(f)

# Update the prompt with the generated_at field
# Save the updated prompts to the prompts file
def update_prompt(prompts, prompt, generated_at):
    for entry in prompts:
        if entry['prompt'] == prompt:
            entry['generated_at'] = generated_at
            break

    with open(PROMPTS_FILE, 'w') as f:
        json.dump(prompts, f, indent=4)


def get_task(args):
    return worker.AsyncTask(args=args)

def generate_clicked(task: worker.AsyncTask):
    import ldm_patched.modules.model_management as model_management

    with model_management.interrupt_processing_mutex:
        model_management.interrupt_processing = False

    if len(task.args) == 0:
        return

    execution_start_time = time.perf_counter()
    finished = False

    worker.async_tasks.append(task)

    while not finished:
        time.sleep(0.01)
        if len(task.yields) > 0:
            flag, product = task.yields.pop(0)
            if flag == 'preview':

                # help bad internet connection by skipping duplicated preview
                if len(task.yields) > 0:  # if we have the next item
                    if task.yields[0][0] == 'preview':   # if the next item is also a preview
                        # print('Skipped one preview for better internet connection.')
                        continue
            if flag == 'results':
                pass
            if flag == 'finish':
                # Upload images to the FastAPI server
                for filepath in product:
                    if isinstance(filepath, str) and os.path.exists(filepath):
                        upload_image(filepath)

                finished = True

                # delete Fooocus temp images, only keep gradio temp images
                if args_manager.args.disable_image_log:
                    for filepath in product:
                        if isinstance(filepath, str) and os.path.exists(filepath):
                            os.remove(filepath)

    execution_time = time.perf_counter() - execution_start_time
    print(f'Total time: {execution_time:.2f} seconds')
    return

# Function to upload images to FastAPI server
def upload_image(image_path):
    try:
        with open(image_path, "rb") as file:
            response = requests.post(FASTAPI_SERVER_URL, files={"file": file})
            if response.status_code == 200:
                print(f"✅ Successfully uploaded {image_path}")
            else:
                print(f"❌ Failed to upload {image_path}: {response.text}")
    except Exception as e:
        print(f"⚠️ Error uploading {image_path}: {e}")


def process_prompt(prompt_text):
    config = [False, prompt_text, 'saturated, high contrast, big nose', ['Fooocus V2', 'Fooocus Photograph', 'Fooocus Negative'], 'Quality', '1344×768 <span style="color: grey;"> ∣ 7:4</span>', 1, 'png', '3453121314987717455', False, 2, 3, 'realisticStockPhoto_v20.safetensors', 'None', 0.5, True, 'SDXL_FILM_PHOTOGRAPHY_STYLE_V1.safetensors', 0.25, True, 'None', 1, True, 'None', 1, True, 'None', 1, True, 'None', 1, False, 'uov', 'Disabled', None, [], None, '', None, False, False, False, False, 1.5, 0.8, 0.3, 7, 2, 'dpmpp_2m_sde_gpu', 'karras', 'Default (model)', -1, -1, -1, -1, -1, -1, False, False, False, False, 64, 128, 'joint', 0.25, False, 1.01, 1.02, 0.99, 0.95, False, False, 'v2.6', 1, 0.618, False, False, 0, False, False, 'fooocus', None, 0.5, 0.6, 'ImagePrompt', None, 0.5, 0.6, 'ImagePrompt', None, 0.5, 0.6, 'ImagePrompt', None, 0.5, 0.6, 'ImagePrompt', False, 0, False, None, True, 'Upscale (1.5x)', 'Before First Enhancement', 'Original Prompts', False, '', '', '', 'sam', 'full', 'vit_b', 0.25, 0.3, 0, False, 'v2.6', 1, 0.618, 0, False, False, '', '', '', 'sam', 'full', 'vit_b', 0.25, 0.3, 0, False, 'v2.6', 1, 0.618, 0, False, False, '', '', '', 'sam', 'full', 'vit_b', 0.25, 0.3, 0, False, 'v2.6', 1, 0.618, 0, False]
    task = get_task(config)
    generate_clicked(task)

def main():
    # config = load_config(CONFIG_FILE)  # Load the configuration from the JSON file
    prompts = load_prompts(PROMPTS_FILE)  # Load the prompts

    print("Processing prompts...")
    print(prompts)

    # Iterating over each prompt to process
    for entry in prompts:
        prompt_text = entry['prompt']
        process_prompt(prompt_text)
        update_prompt(prompts, prompt_text, time.time())

    print("All prompts have been processed.")
