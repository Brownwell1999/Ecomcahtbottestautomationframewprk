# os is Python's built-in module for talking to the operating system. 
    # Here it is used for one thing: reading environment variables.



import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

# The project root is two folders above this file (framework/utils/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DATA_DIR = PROJECT_ROOT / "test_data"

# Quality gates from thresholds.yaml: THRESHOLDS["metrics"]["answer_relevancy"], THRESHOLDS["limits"]["max_answer_words"]
THRESHOLDS = yaml.safe_load((PROJECT_ROOT / "thresholds.yaml").read_text(encoding="utf-8"))


def load_test_data(name):
    """Read a JSON file from test_data/, e.g. load_test_data("chatbot/answer_relevancy.json")."""
    return json.loads((TEST_DATA_DIR / name).read_text(encoding="utf-8"))

GRAPHQL_URL = os.getenv("CHATBOT_GRAPHQL_URL", "http://localhost:5173/graphql")

# Judge LLM used by the DeepEval metrics: any provider with an OpenAI-compatible API (Gemini, Groq, ...).
# A different model family AND provider than ShopBot's own (openai/gpt-oss-20b on Groq), so the bot
# doesn't grade itself and eval runs don't use up ShopBot's rate limit.
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY")
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3.8-flash")


r"""
Path(...) turns that text into a Path object (from pathlib). A Path knows about folders, 
so you can ask for its parent folder or join paths with /. Plain text can't do that.

.resolve() turns the path into a full, absolute one. It matters if the file was reached 
through a relative path such as ..\framework\utils\config.py.

.parents[2] walks up the folder tree: 
The 2 means "go up two folders from the file's own folder".

/ "test_data" joins the project root and test_data. Path uses / to build paths, so you don't need to worry about Windows \ or Linux /.

Result: TEST_DATA_DIR is C:\Ecomchatboattestautomation\test_data.

.read_text(encoding="utf-8") : Opens the file and returns its contents as one string

json.loads(...)	Converts JSON text into Python data	: a Python list of strings

"""