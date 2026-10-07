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

# Which version of the golden datasets is in test_data/ (shown in every test report, so runs can be compared)
DATASET_VERSION = str(yaml.safe_load((TEST_DATA_DIR / "dataset_version.yaml").read_text(encoding="utf-8"))["version"])


def load_test_data(name):
    """Read a JSON file from test_data/, e.g. load_test_data("chatbot/answer_relevancy.json")."""
    return json.loads((TEST_DATA_DIR / name).read_text(encoding="utf-8"))

GRAPHQL_URL = os.getenv("CHATBOT_GRAPHQL_URL", "http://localhost:5173/graphql")

# Judge LLM used by the DeepEval metrics: Claude (Anthropic). A different model family and provider than
# ShopBot's own (openai/gpt-oss-20b on Groq), so the bot doesn't grade itself and eval runs don't use up ShopBot's quota.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-sonnet-5-5")

# LangSmith: where ShopBot records every conversation turn as a trace. The online evaluation job
# (online_eval/) reads traces from this project and writes its scores back onto them.
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "shopbot-dev")

# Where ShopBot's own repo is on this machine. Used only by the dataset tools (dataset_tools/):
# the knowledge base is the source for synthetic goldens, and thumbs-down feedback is read from its database.
SHOPBOT_DIR = Path(os.getenv("SHOPBOT_DIR", "C:/Ecomchatboat"))
KNOWLEDGE_BASE_DIR = Path(os.getenv("SHOPBOT_KNOWLEDGE_BASE_DIR", str(SHOPBOT_DIR / "data" / "knowledge_base")))


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