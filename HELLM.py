import os

import tiktoken
import yaml
import numpy as np
import gymnasium as gym
from gymnasium.wrappers import RecordVideo
from langchain_community.llms import LlamaCpp, Ollama
from langchain_community.chat_models import AzureChatOpenAI, ChatOllama
from langchain_ollama import ChatOllama
from langchain_openai import OpenAI

import highway_env
from scenario.scenario import Scenario
from LLMDriver.driverAgent import DriverAgent
from LLMDriver.outputAgent import OutputParser
from LLMDriver.customTools import (
    getAvailableActions,
    getAvailableLanes,
    getLaneInvolvedCar,
    isChangeLaneConflictWithCar,
    isAccelerationConflictWithCar,
    isKeepSpeedConflictWithCar,
    isDecelerationSafe,
    isActionSafe,
)

OPENAI_CONFIG = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)

if OPENAI_CONFIG['OPENAI_API_TYPE'] == 'azure':
    # os.environ["OPENAI_API_TYPE"] = OPENAI_CONFIG['OPENAI_API_TYPE']
    # os.environ["OPENAI_API_VERSION"] = OPENAI_CONFIG['AZURE_API_VERSION']
    # os.environ["OPENAI_API_BASE"] = OPENAI_CONFIG['AZURE_API_BASE']
    # os.environ["OPENAI_API_KEY"] = OPENAI_CONFIG['AZURE_API_KEY']
    # llm = AzureChatOpenAI(
    #     deployment_name=OPENAI_CONFIG['AZURE_MODEL'],
    #     temperature=0,
    #     max_tokens=1024,
    #     request_timeout=60
    # )
    ...
elif OPENAI_CONFIG['OPENAI_API_TYPE'] == 'openai':
    os.environ["OPENAI_API_KEY"] = OPENAI_CONFIG['OPENAI_KEY']
    llm = OpenAI(
        temperature=0,
        model='gpt-3.5-turbo-1106',  # or any other model with 8k+ context
        max_tokens=1024,
        timeout=60
    )

# base setting
# llm = LlamaCpp(
#     n_gpu_layers=-1,
#     model_path="/mnt/a4ceb600-eb8a-411c-ac16-e68b8312a0c5/aims/PycharmProjects/reports-service/language_models/Llama-3.1-WhiteRabbitNeo-2-8B-Q6_K_L.gguf",
#     temperature=0,
#     max_tokens=1024,
#     n_ctx=30000,
# verbose = True
# )
# available_encodings = tiktoken.list_encoding_names()
# print("Available encodings:", available_encodings)
# encoder = tiktoken.get_encoding("o200k_base")
# llm = OpenAI(
#     base_url="http://192.168.100.91:11434",
#     api_key="dummy",
#     max_tokens=1024,
#     model="qwq",
#     timeout=60,
#     verbose=True)

llm = ChatOllama(
    base_url="http://192.168.100.52:11434",
    temperature=0,
    model="gemma3:12b-it-q8_0",
    verbose=True,
    num_predict=1024)
# # environment setting
vehicleCount = 15
config = {
    "observation": {
        "type": "Kinematics",
        "features": ["presence", "x", "y", "vx", "vy"],
        "absolute": True,
        "normalize": False,
        "vehicles_count": vehicleCount,
        "see_behind": True,
    },
    "action": {
        "type": "ContinuousAction",
        "target_speeds": np.linspace(0, 32, 9),
    },
    "lanes_count": 4,
    "scaling": 8,
    "screen_width": 1700,  # [px]
    "screen_height": 300,  # [px]
    "duration": 40,
    "vehicles_density": 2,
    "show_trajectories": True,
    "render_agent": True,
    "policy_frequency": 5,
    "simulation_frequency": 5,
}

print(gym.envs.registry.keys())
env = gym.make('highway-v0', render_mode="rgb_array")
env.unwrapped.configure(config)
env = RecordVideo(
    env, './results-video',
    name_prefix=f"highwayv0",
)
env.unwrapped.set_record_video_wrapper(env)
obs, info = env.reset()
env.render()
# scenario and driver agent setting
if not os.path.exists('results-db/'):
    os.mkdir('results-db')
database = f"results-db/highwayv0.db"
sce = Scenario(vehicleCount, database)
toolModels = [
    getAvailableActions(env),
    getAvailableLanes(sce),
    getLaneInvolvedCar(sce),
    isChangeLaneConflictWithCar(sce),
    isAccelerationConflictWithCar(sce),
    isKeepSpeedConflictWithCar(sce),
    isDecelerationSafe(sce),
    isActionSafe(),
]
DA = DriverAgent(llm, toolModels, sce, verbose=True)
outputParser = OutputParser(sce, llm)
output = None
done = truncated = False
frame = 0
try:
    print(env.action_space.sample())
    while not (done or truncated):
        sce.upateVehicles(obs, frame)
        DA.agentRun(output)
        da_output = DA.exportThoughts()
        output = outputParser.agentRun(da_output)
        env.render()
        env.unwrapped.automatic_rendering_callback = env.video_recorder.capture_frame()
        obs, reward, done, info, _ = env.step(np.array([output["acceleration"], output["angle"]], dtype=np.float32))
        print(output)
        frame += 1
finally:
    env.close()
