# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import urllib.parse
import urllib.request

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

MODEL = "gemini-3.6-flash"


def search_code_repositories(
    query: str, target_mcu: str = "STM32", language: str = "cpp", platform: str = "github"
) -> str:
    """Queries code repositories (GitHub or Codeberg) for embedded software driver implementations, file trees, and metadata.

    Args:
        query: Search query for driver or peripheral (e.g., 'SPI NOR Flash', 'I2C Sensor', 'CAN driver').
        target_mcu: Target hardware platform or toolchain (e.g., 'STM32', 'ARM GCC', 'Cortex-M', 'RP2040').
        language: Programming language filter ('cpp', 'rust', or 'c').
        platform: Repository hosting platform ('github' or 'codeberg').

    Returns:
        JSON string containing matching repositories, metadata, file tree links, stars, and commit dates.
    """
    if platform.lower() == "codeberg":
        search_term = f"{query} {target_mcu}"
        encoded_query = urllib.parse.quote_plus(search_term)
        url = f"https://codeberg.org/api/v1/repos/search?q={encoded_query}&limit=5"
        req = urllib.request.Request(
            url, headers={"User-Agent": "EmbeddedDriverFinderAgent/1.0"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                results = []
                for item in items:
                    full_name = item.get("full_name")
                    html_url = item.get("html_url")
                    results.append(
                        {
                            "platform": "Codeberg",
                            "repository": full_name,
                            "repo_url": html_url,
                            "description": item.get("description", "No description."),
                            "stars": item.get("stars_count", 0),
                            "last_commit_date": item.get("updated_at", "N/A"),
                            "latest_release": "Codeberg Repo",
                            "matching_files": [
                                {"path": "Repository Link", "url": html_url}
                            ],
                        }
                    )
                return json.dumps(
                    {
                        "query": search_term,
                        "platform": "Codeberg",
                        "count": len(results),
                        "repositories": results,
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": f"Failed to search Codeberg: {str(e)}"})

    headers = {
        "User-Agent": "EmbeddedDriverFinderAgent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    github_lang = "cpp"
    if language.lower() in ["rust", "rs"]:
        github_lang = "rust"
    elif language.lower() == "c":
        github_lang = "c"

    search_term = f"{query} {target_mcu} language:{github_lang}".strip()
    encoded_query = urllib.parse.quote_plus(search_term)
    url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            items = data.get("items", [])[:5]

            exts = [".hpp", ".h", ".cpp", ".cc"]
            if github_lang == "rust":
                exts = [".rs"]
            elif github_lang == "c":
                exts = [".h", ".c"]

            results = []
            for item in items:
                owner_repo = item.get("full_name")
                stars = item.get("stargazers_count", 0)
                pushed_at = item.get("pushed_at", "N/A")
                default_branch = item.get("default_branch", "main")

                rel_url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
                rel_req = urllib.request.Request(rel_url, headers=headers)
                latest_release = "No official release tag"
                try:
                    with urllib.request.urlopen(rel_req) as rel_resp:
                        rel_data = json.loads(rel_resp.read().decode("utf-8"))
                        tag = rel_data.get("tag_name")
                        pub = rel_data.get("published_at")
                        latest_release = f"{tag} ({pub})"
                except Exception:
                    pass

                tree_url = f"https://api.github.com/repos/{owner_repo}/git/trees/{default_branch}?recursive=1"
                tree_req = urllib.request.Request(tree_url, headers=headers)
                matching_files = []
                try:
                    with urllib.request.urlopen(tree_req) as tree_resp:
                        tree_data = json.loads(tree_resp.read().decode("utf-8"))
                        for t_item in tree_data.get("tree", []):
                            path = t_item.get("path", "")
                            if t_item.get("type") == "blob" and any(
                                path.lower().endswith(ext) for ext in exts
                            ):
                                file_url = f"https://github.com/{owner_repo}/blob/{default_branch}/{path}"
                                matching_files.append({"path": path, "url": file_url})
                except Exception:
                    pass

                results.append(
                    {
                        "platform": "GitHub",
                        "repository": owner_repo,
                        "repo_url": item.get("html_url"),
                        "description": item.get("description", "No description."),
                        "stars": stars,
                        "last_commit_date": pushed_at,
                        "latest_release": latest_release,
                        "matching_files": matching_files[:10],
                    }
                )

            return json.dumps(
                {
                    "query": search_term,
                    "platform": "GitHub",
                    "count": len(results),
                    "repositories": results,
                },
                indent=2,
            )

    except Exception as e:
        return json.dumps({"error": f"Failed to search GitHub: {str(e)}"})


def fetch_github_file_content(
    repo_full_name: str, file_path: str, branch: str = "main"
) -> str:
    """Fetches raw content of a specific file from a GitHub repository.

    Args:
        repo_full_name: Repository in 'owner/repo' format.
        file_path: Relative path to file (e.g. 'include/spi_flash.hpp').
        branch: Git branch name.

    Returns:
        Raw text content of the file or error message.
    """
    raw_url = (
        f"https://raw.githubusercontent.com/{repo_full_name}/{branch}/{file_path}"
    )
    req = urllib.request.Request(
        raw_url, headers={"User-Agent": "EmbeddedDriverFinderAgent/1.0"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            content = response.read().decode("utf-8", errors="replace")
            if len(content) > 4000:
                content = content[:4000] + "\n... [content truncated]"
            return content
    except Exception as e:
        if branch == "main":
            return fetch_github_file_content(
                repo_full_name, file_path, branch="master"
            )
        return f"Error fetching file {file_path} from {repo_full_name}: {str(e)}"


# WRITE: after each turn, send the session to Memory Bank for extraction and persistence.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are an Embedded Systems Software Engineering Agent specializing in C++ (C++20/C++23), "
        "Rust, and C driver implementations for ARM, STM32, and microcontroller platforms.\n\n"
        "CORE RESPONSE REQUIREMENTS:\n"
        "1. ALWAYS inspect PRELOADED MEMORIES at the start of each turn to recall previously discovered "
        "repositories, their confidence ratings, file URLs, and driver details.\n"
        "2. Query and list any relevant remembered repositories first in your output.\n"
        "3. NEXT, perform new live searches using `search_code_repositories` and `fetch_github_file_content` "
        "for embedded drivers matching the user request and specified programming language (C++, Rust, or C) and platform (GitHub or Codeberg).\n"
        "4. For EACH repository presented (both from memory and newly searched), provide:\n"
        "   - Repository Link & Name: e.g. [owner/repo](https://github.com/owner/repo) or [owner/repo](https://codeberg.org/owner/repo)\n"
        "   - Platform Badge: 🐙 GitHub or 🏔️ Codeberg\n"
        "   - Match Confidence Score: e.g., '92% Match (High Confidence)' or '45% Match (Partial Match)'. "
        "     Rate 90%+ for modern C++20/Rust/C drivers matching requested hardware platform and peripheral. "
        "     Rate 30-50% for legacy code or partial matches.\n"
        "   - Metadata:\n"
        "     * ⭐ Stars: Number of stargazers\n"
        "     * 📅 Last Commit Date: Date of last push\n"
        "     * 🏷️ Latest Release Version & Date: Release tag or 'No official release tag'\n"
        "   - Specific Matching File Links: Direct markdown links to source/header/RS files inside the repository.\n"
        "   - Comparison & Architectural Summary: Language idioms used (C++20 concepts/RAII, Rust safe HAL/embedded-hal traits, or C drivers), pros/cons, and confidence rationale.\n"
        "5. AUTOMATIC MEMORY SAVING SECTION:\n"
        "   At the very end of your response, ALWAYS include a dedicated section titled:\n"
        "   '### 📌 Discovered Repositories Registered to Memory'\n"
        "   Format each item clearly as: 'REGISTERED_REPO: owner/repo | PLATFORM: site | FILES: url1, url2 | CONFIDENCE: X% | TARGET: platform'. "
        "   This explicit structured format enables Vertex AI Memory Bank to reliably persist these repositories into cross-session memory."
    ),
    tools=[
        PreloadMemoryTool(),
        search_code_repositories,
        fetch_github_file_content,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
