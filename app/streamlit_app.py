from __future__ import annotations

import base64
import os
from pathlib import Path
from textwrap import dedent

import requests
import streamlit as st
from PIL import Image, ImageEnhance

from agent.tools import execute_tool


# ============================================================
# CONFIG
# ============================================================

BACKEND_URL = os.getenv(
    "AGENTFORGE_BACKEND_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

API_URL = f"{BACKEND_URL}/api/v1/run"
HEALTH_URL = f"{BACKEND_URL}/docs"

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

MASCOT_PATH = ASSETS_DIR / "agentforge_mascot.png"
LAB_PATH = ASSETS_DIR / "agentforge_assets.png"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AgentForge",
    page_icon="⚒️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_MISSION = (
    "Find the best laptop under ₹80000 "
    "for machine learning development "
    "and recommend one using evidence."
)

DEFAULTS = {
    "mission": DEFAULT_MISSION,
    "main_mission": DEFAULT_MISSION,
    "builder_mission": DEFAULT_MISSION,
    "chaos_task": DEFAULT_MISSION,
    "result": None,
    "missions_run": 0,
    "builder_steps": 5,
    "builder_chaos": False,
    "builder_failure": "Tool timeout",
    "builder_model": "Gemini",
    "theme_density": "Comfortable",
    "show_console": True,
    "sidebar_tool_result": None,
    "sidebar_tool_choice": "🔎 Search Catalog",
    "sidebar_search_query": "",
    "sidebar_calculator_expression": "",
    "sidebar_docs_query": "",
    "sidebar_compare_budget": 80000,
    "chaos_failure": "Tool timeout",
}

for key, value in DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def html(content: str) -> None:
    st.html(
        dedent(content)
    )


def set_example_mission() -> None:

    st.session_state.mission = DEFAULT_MISSION
    st.session_state.main_mission = DEFAULT_MISSION
    st.session_state.builder_mission = DEFAULT_MISSION
    st.session_state.chaos_task = DEFAULT_MISSION


def new_mission() -> None:

    st.session_state.mission = ""
    st.session_state.main_mission = ""
    st.session_state.builder_mission = ""
    st.session_state.chaos_task = ""

    st.session_state.result = None
    st.session_state.sidebar_tool_result = None


def clear_current_run() -> None:

    st.session_state.result = None


# ============================================================
# IMAGE HELPERS
# ============================================================

@st.cache_resource
def load_mascot() -> Image.Image | None:

    if not MASCOT_PATH.exists():
        return None

    try:

        image = Image.open(
            MASCOT_PATH
        ).convert("RGBA")

        image = ImageEnhance.Sharpness(
            image
        ).enhance(1.45)

        image = ImageEnhance.Contrast(
            image
        ).enhance(1.05)

        return image

    except Exception:

        return None


@st.cache_resource
def load_lab() -> Image.Image | None:

    if not LAB_PATH.exists():
        return None

    try:

        image = Image.open(
            LAB_PATH
        ).convert("RGB")

        image = ImageEnhance.Sharpness(
            image
        ).enhance(1.2)

        return image

    except Exception:

        return None


MASCOT = load_mascot()
LAB = load_lab()


# ============================================================
# MASCOT BASE64
# ============================================================

MASCOT_B64 = ""

if MASCOT_PATH.exists():

    try:

        MASCOT_B64 = base64.b64encode(
            MASCOT_PATH.read_bytes()
        ).decode(
            "utf-8"
        )

    except Exception:

        MASCOT_B64 = ""


# ============================================================
# BACKEND STATUS
# ============================================================

def backend_is_online() -> bool:

    try:

        response = requests.get(
            HEALTH_URL,
            timeout=1.2,
        )

        return response.ok

    except requests.RequestException:

        return False


# ============================================================
# API ERROR FORMATTER
# ============================================================

def extract_api_error(
    response: requests.Response,
) -> str:

    try:

        payload = response.json()

    except ValueError:

        return (
            f"Request failed with HTTP "
            f"{response.status_code}."
        )

    detail = payload.get(
        "detail"
    )

    if isinstance(
        detail,
        str,
    ):

        return detail

    if isinstance(
        detail,
        dict,
    ):

        return str(detail)

    error = payload.get(
        "error"
    )

    if isinstance(
        error,
        dict,
    ):

        return error.get(
            "message",
            str(error),
        )

    return str(
        payload
    )


# ============================================================
# MISSION EXECUTION
# ============================================================

def execute_mission(
    task: str,
    chaos_mode: bool = False,
    chaos_type: str = "Tool timeout",
) -> dict | None:

    task = task.strip()

    if len(task) < 10:

        st.error(
            "Give AgentForge a more detailed mission."
        )

        return None

    try:

        with st.spinner(
            "⚡ Forging your mission..."
        ):

            response = requests.post(
                API_URL,
                json={
                    "task": task,
                    "chaos_mode": chaos_mode,
                    "chaos_type": chaos_type,
                },
                timeout=120,
            )

        if response.status_code == 429:

            st.error(
                "Gemini quota is currently exhausted. "
                "AgentForge is working correctly, but "
                "the AI provider has reached its current "
                "request limit. Please try again after "
                "the quota resets or billing is enabled."
            )

            return None

        if response.status_code >= 400:

            st.error(
                extract_api_error(
                    response
                )
            )

            return None

        result = response.json()

        st.session_state.result = result
        st.session_state.mission = task
        st.session_state.main_mission = task
        st.session_state.builder_mission = task
        st.session_state.chaos_task = task
        st.session_state.missions_run += 1

        return result

    except requests.exceptions.ConnectionError:

        st.error(
            "AgentForge cannot reach the FastAPI backend."
        )

    except requests.exceptions.Timeout:

        st.error(
            "Agent execution timed out."
        )

    except requests.exceptions.RequestException as exc:

        st.error(
            f"AgentForge request failed: {exc}"
        )

    except ValueError:

        st.error(
            "AgentForge received an invalid API response."
        )

    return None


# ============================================================
# TOOL RESULT RENDERERS
# ============================================================

def render_search_catalog_result(
    result: dict,
) -> None:

    results = result.get(
        "results",
        [],
    )

    count = result.get(
        "count",
        len(results),
    )

    html(
    f"""
    <div style="
        margin-top:8px;
        padding:12px;
        background:#0F0B17;
        border:1px solid #44335A;
        border-radius:10px;
    ">

        <div style="
            color:#2FE7FF;
            font-size:9px;
            font-weight:900;
            letter-spacing:2px;
            margin-bottom:9px;
        ">
            🔎 SEARCH RESULTS · {count}
        </div>
    """
    )

    if not results:

        html(
        """
        <div style="
            color:#9B90A5;
            font-size:10px;
            padding:5px 0;
        ">
            No matching products found.
        </div>
        """
        )

    else:

        for index, item in enumerate(
            results
        ):

            name = item.get(
                "name",
                "Unknown product",
            )

            price = item.get(
                "price",
            )

            ram = item.get(
                "ram_gb",
            )

            gpu = item.get(
                "gpu",
                "—",
            )

            battery = item.get(
                "battery_hours",
            )

            score = item.get(
                "score",
            )

            price_text = (
                f"₹{price:,.0f}"
                if isinstance(
                    price,
                    (int, float),
                )
                else "—"
            )

            ram_text = (
                f"{ram} GB"
                if ram is not None
                else "—"
            )

            battery_text = (
                f"{battery}h"
                if battery is not None
                else "—"
            )

            score_text = (
                str(score)
                if score is not None
                else "—"
            )

            border = (
                "border-bottom:1px solid #2C2338;"
                if index < len(results) - 1
                else ""
            )

            html(
            f"""
            <div style="
                padding:9px 0;
                {border}
            ">

                <div style="
                    color:#FFFFFF;
                    font-size:11px;
                    font-weight:900;
                ">
                    {name}
                </div>

                <div style="
                    color:#2FE7FF;
                    font-size:11px;
                    font-weight:900;
                    margin-top:3px;
                ">
                    {price_text}
                </div>

                <div style="
                    color:#AAA0B4;
                    font-size:8.5px;
                    margin-top:3px;
                    line-height:1.45;
                ">
                    {ram_text} RAM
                    &nbsp;·&nbsp;
                    {gpu}
                    &nbsp;·&nbsp;
                    {battery_text} battery
                </div>

                <div style="
                    color:#FFD42E;
                    font-size:8.5px;
                    font-weight:900;
                    margin-top:3px;
                ">
                    SCORE {score_text}
                </div>

            </div>
            """
            )

    html(
    """
    </div>
    """
    )


def render_calculator_result(
    result: dict,
) -> None:

    expression = result.get(
        "expression",
        "—",
    )

    value = result.get(
        "result",
        "—",
    )

    try:

        value_text = f"{float(value):,.2f}"

        if value_text.endswith(".00"):

            value_text = value_text[:-3]

    except (
        ValueError,
        TypeError,
    ):

        value_text = str(value)

    html(
    f"""
    <div style="
        margin-top:8px;
        padding:12px;
        background:#0F0B17;
        border:1px solid #44335A;
        border-radius:10px;
    ">

        <div style="
            color:#2FE7FF;
            font-size:9px;
            font-weight:900;
            letter-spacing:2px;
        ">
            🧮 CALCULATION
        </div>

        <div style="
            color:#BEB3C9;
            font-family:Consolas,monospace;
            font-size:10px;
            margin-top:8px;
            word-break:break-word;
        ">
            {expression}
        </div>

        <div style="
            color:#83778E;
            font-size:8px;
            font-weight:900;
            letter-spacing:2px;
            margin-top:11px;
        ">
            RESULT
        </div>

        <div style="
            color:#31FF9B;
            font-family:'Bangers',Impact,sans-serif;
            font-size:28px;
            margin-top:2px;
        ">
            {value_text}
        </div>

    </div>
    """
    )


def render_compare_result(
    result: dict,
) -> None:

    budget = result.get(
        "budget",
        0,
    )

    candidates = result.get(
        "candidates",
        [],
    )

    recommendation = result.get(
        "recommendation",
    )

    html(
    f"""
    <div style="
        margin-top:8px;
        padding:12px;
        background:#0F0B17;
        border:1px solid #44335A;
        border-radius:10px;
    ">

        <div style="
            color:#2FE7FF;
            font-size:9px;
            font-weight:900;
            letter-spacing:2px;
        ">
            📊 COMPARISON
        </div>

        <div style="
            color:#968A9F;
            font-size:9px;
            margin-top:5px;
        ">
            Budget: ₹{float(budget):,.0f}
        </div>
    """
    )

    if recommendation:

        name = recommendation.get(
            "name",
            "Unknown",
        )

        price = recommendation.get(
            "price",
            0,
        )

        ram = recommendation.get(
            "ram_gb",
            "—",
        )

        gpu = recommendation.get(
            "gpu",
            "—",
        )

        battery = recommendation.get(
            "battery_hours",
            "—",
        )

        score = recommendation.get(
            "score",
            "—",
        )

        battery_text = (
            f"{battery}h"
            if isinstance(
                battery,
                (int, float),
            )
            else str(battery)
        )

        html(
        f"""
        <div style="
            margin-top:10px;
            padding:10px;
            background:#17111F;
            border:1px solid #553D70;
            border-radius:8px;
        ">

            <div style="
                color:#FFD42E;
                font-size:8px;
                font-weight:900;
                letter-spacing:2px;
            ">
                BEST MATCH
            </div>

            <div style="
                color:#FFFFFF;
                font-size:13px;
                font-weight:900;
                margin-top:4px;
            ">
                {name}
            </div>

            <div style="
                color:#2FE7FF;
                font-size:12px;
                font-weight:900;
                margin-top:4px;
            ">
                ₹{price:,.0f}
            </div>

            <div style="
                color:#AAA0B4;
                font-size:8.5px;
                line-height:1.5;
                margin-top:4px;
            ">
                {ram} GB RAM
                &nbsp;·&nbsp;
                {gpu}
                &nbsp;·&nbsp;
                {battery_text}
            </div>

            <div style="
                color:#FFD42E;
                font-size:8.5px;
                font-weight:900;
                margin-top:4px;
            ">
                SCORE {score}
            </div>

        </div>
        """
        )

    else:

        html(
        """
        <div style="
            color:#9B90A5;
            font-size:10px;
            margin-top:8px;
        ">
            No products fit this budget.
        </div>
        """
        )

    html(
    f"""
        <div style="
            color:#83778E;
            font-size:8px;
            margin-top:8px;
        ">
            {len(candidates)} candidates evaluated
        </div>

    </div>
    """
    )


def render_docs_result(
    result: dict,
) -> None:

    results = result.get(
        "results",
        [],
    )

    count = result.get(
        "count",
        len(results),
    )

    html(
    f"""
    <div style="
        margin-top:8px;
        padding:12px;
        background:#0F0B17;
        border:1px solid #44335A;
        border-radius:10px;
    ">

        <div style="
            color:#2FE7FF;
            font-size:9px;
            font-weight:900;
            letter-spacing:2px;
        ">
            📚 DOCUMENT RESULTS · {count}
        </div>
    """
    )

    if not results:

        html(
        """
        <div style="
            color:#9B90A5;
            font-size:10px;
            margin-top:8px;
        ">
            No matching documents found.
        </div>
        """
        )

    else:

        for index, document in enumerate(
            results
        ):

            title = document.get(
                "title",
                "Untitled",
            )

            content = document.get(
                "content",
                "",
            )

            if len(content) > 170:

                content = (
                    content[:167]
                    + "..."
                )

            border = (
                "border-bottom:1px solid #2C2338;"
                if index < len(results) - 1
                else ""
            )

            html(
            f"""
            <div style="
                padding:9px 0;
                {border}
            ">

                <div style="
                    color:#FFFFFF;
                    font-size:10px;
                    font-weight:900;
                ">
                    {title}
                </div>

                <div style="
                    color:#AAA0B4;
                    font-size:8.5px;
                    line-height:1.5;
                    margin-top:4px;
                ">
                    {content}
                </div>

            </div>
            """
            )

    html(
    """
    </div>
    """
    )


def render_sidebar_tool_result(
    result: dict | None,
) -> None:

    if not result:
        return

    if "recommendation" in result:

        render_compare_result(
            result
        )

    elif "expression" in result:

        render_calculator_result(
            result
        )

    elif "results" in result:

        query = str(
            result.get(
                "query",
                "",
            )
        ).lower()

        doc_queries = {
            "timeout",
            "memory",
            "deployment",
            "incident",
            "upstream",
            "latency",
            "connection",
            "retry",
            "configuration",
            "leak",
        }

        if any(
            word in query
            for word in doc_queries
        ):

            render_docs_result(
                result
            )

        else:

            render_search_catalog_result(
                result
            )


# ============================================================
# GLOBAL CSS
# ============================================================

html(
"""
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;600;700;800;900&family=Permanent+Marker&display=swap'
);


/* ==========================================================
   GLOBAL
   ========================================================== */

.stApp {

    background:
        radial-gradient(
            circle at 8% 0%,
            rgba(112,40,255,.22),
            transparent 23%
        ),
        radial-gradient(
            circle at 94% 3%,
            rgba(255,38,135,.13),
            transparent 22%
        ),
        #08070D;

    color:#FFFFFF;
}


.block-container {

    max-width:1540px;

    padding-top:12px;
    padding-bottom:45px;
    padding-left:20px;
    padding-right:20px;
}


.stApp,
.stApp * {

    font-family:
        "Nunito",
        "Segoe UI",
        sans-serif;
}


[data-testid="stHeader"] {

    height:0 !important;
    background:transparent !important;
}


[data-testid="stToolbar"] {

    display:none !important;
}


#MainMenu,
footer {

    visibility:hidden !important;
}


/* ==========================================================
   SIDEBAR
   ========================================================== */

section[data-testid="stSidebar"] {

    background:
        radial-gradient(
            circle at 50% 0%,
            rgba(111,47,255,.30),
            transparent 29%
        ),
        radial-gradient(
            circle at 12% 88%,
            rgba(0,220,255,.07),
            transparent 25%
        ),
        #09070F;

    border-right:
        1px solid #382052;

    box-shadow:
        8px 0 35px rgba(0,0,0,.35);
}


section[data-testid="stSidebar"] .block-container {

    padding:
        16px 14px;
}


section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {

    color:
        #FFFFFF !important;
}


.sidebar-brand {

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        48px;

    line-height:
        .82;

    letter-spacing:
        1px;

    color:
        #FFFFFF !important;

    text-shadow:
        3px 3px 0 #7135FF,
        7px 7px 0 #FF2E88;
}


.sidebar-brand span {

    color:
        #2FE6FF !important;
}


.sidebar-sub {

    margin-top:
        8px;

    color:
        #9D92AC !important;

    font-size:
        9px;

    font-weight:
        900;

    letter-spacing:
        3px;

    text-transform:
        uppercase;
}


.sidebar-card {

    margin-top:
        16px;

    padding:
        12px;

    border:
        1px solid #44335A;

    border-radius:
        12px;

    background:
        #0E0B16;
}


.sidebar-label {

    color:
        #83778E !important;

    font-size:
        8px;

    font-weight:
        900;

    letter-spacing:
        2px;

    text-transform:
        uppercase;
}


.sidebar-value {

    margin-top:
        6px;

    color:
        #FFFFFF !important;

    font-size:
        10px;

    line-height:
        1.45;

    font-weight:
        800;
}


.sidebar-status {

    margin-top:
        12px;

    padding:
        12px;

    border:
        1px solid #44335A;

    border-radius:
        12px;

    background:
        #0E0B16;
}


.online {

    margin-top:
        3px;

    color:
        #31FF9B !important;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        26px;
}


.offline {

    margin-top:
        3px;

    color:
        #FF526F !important;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        26px;
}


section[data-testid="stSidebar"]
.stTextInput input {

    background:
        #FFF9E8 !important;

    color:
        #1B1520 !important;

    border:
        1px solid #18131A !important;

    border-radius:
        7px !important;

    font-size:
        10px !important;
}


section[data-testid="stSidebar"]
div[data-baseweb="select"] > div {

    background:
        #17111F !important;

    color:
        #FFFFFF !important;

    border:
        1px solid #44355B !important;

    border-radius:
        8px !important;
}


/* ==========================================================
   SIDEBAR BUTTONS
   ========================================================== */

section[data-testid="stSidebar"]
.stButton > button {

    min-height:
        38px !important;

    margin-top:
        4px;

    border-radius:
        8px !important;

    font-size:
        10px !important;

    font-weight:
        900 !important;
}


section[data-testid="stSidebar"]
.stButton > button[kind="primary"] {

    background:
        linear-gradient(
            135deg,
            #FF5833,
            #FF2F88
        ) !important;

    color:
        #FFFFFF !important;

    border:
        1px solid #FF87B7 !important;

    box-shadow:
        3px 3px 0 #08070D !important;
}


/* ==========================================================
   MOTTO
   ========================================================== */

.motto {

    margin-top:
        20px;

    text-align:
        center;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        22px;

    line-height:
        .98;

    color:
        #FFFFFF !important;

    transform:
        rotate(-3deg);

    text-shadow:
        2px 2px 0 #7135FF;
}


.motto-pink {

    color:
        #FF318A !important;
}


.motto-cyan {

    color:
        #2FE6FF !important;
}


/* ==========================================================
   TOP BAR
   ========================================================== */

.brand {

    color:
        #FFFFFF !important;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        22px;

    letter-spacing:
        1px;
}


.search-box {

    padding:
        11px 16px;

    background:
        #100D18;

    border:
        1px solid #3D324B;

    border-radius:
        12px;

    color:
        #958A9F !important;

    font-size:
        12px;
}


.gemini-pill {

    padding:
        10px 15px;

    background:
        linear-gradient(
            135deg,
            #7135FF,
            #A43EFF
        );

    border:
        1px solid #B192FF;

    border-radius:
        999px;

    color:
        #FFFFFF !important;

    font-size:
        11px;

    font-weight:
        950;

    text-align:
        center;
}


/* ==========================================================
   HERO
   ========================================================== */

.hero {

    position:
        relative;

    min-height:
        455px;

    overflow:
        hidden;

    border:
        1px solid #4D297B;

    border-radius:
        18px;

    background:
        radial-gradient(
            circle at 79% 40%,
            rgba(0,229,255,.15),
            transparent 24%
        ),
        radial-gradient(
            circle at 33% 34%,
            rgba(111,49,255,.30),
            transparent 42%
        ),
        linear-gradient(
            125deg,
            #19092E,
            #170A31 57%,
            #080D20
        );

    box-shadow:
        inset 0 0 90px rgba(105,42,255,.11),
        0 18px 45px rgba(0,0,0,.35);
}


.hero-dots {

    position:
        absolute;

    inset:
        0;

    opacity:
        .12;

    background-image:
        radial-gradient(
            white 1px,
            transparent 1px
        );

    background-size:
        25px 25px;
}


.hero-copy {

    position:
        relative;

    z-index:
        8;

    width:
        53%;

    padding:
        34px 20px 34px 35px;
}


.kicker {

    display:
        inline-block;

    padding:
        8px 12px;

    background:
        #FFD42E;

    color:
        #18120B !important;

    font-size:
        10px;

    font-weight:
        950;

    letter-spacing:
        1px;

    transform:
        rotate(-1deg);

    box-shadow:
        4px 4px 0 #7135FF;
}


.hero-title {

    margin-top:
        21px;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        clamp(58px,5.7vw,88px);

    line-height:
        .80;

    letter-spacing:
        2px;

    color:
        #FFFFFF !important;

    text-shadow:
        5px 5px 0 #110A18,
        9px 9px 0 #7135FF;
}


.hero-pink {

    color:
        #FF318A !important;
}


.hero-cyan {

    color:
        #2FE6FF !important;
}


.hero-description {

    margin-top:
        21px;

    max-width:
        555px;

    color:
        #DED2E9 !important;

    font-size:
        14px;

    line-height:
        1.62;
}


/* ==========================================================
   HERO ROBOT
   ========================================================== */

.hero-robot {

    position:
        absolute;

    right:
        1%;

    bottom:
        -3%;

    width:
        43%;

    height:
        94%;

    z-index:
        5;

    display:
        flex;

    align-items:
        flex-end;

    justify-content:
        center;

    pointer-events:
        none;
}


.hero-robot img {

    width:
        100%;

    height:
        100%;

    object-fit:
        contain;

    object-position:
        center bottom;

    filter:
        drop-shadow(
            0 24px 28px rgba(0,0,0,.56)
        );
}


.speech {

    position:
        absolute;

    right:
        5.5%;

    top:
        8%;

    z-index:
        12;

    width:
        150px;

    padding:
        11px;

    background:
        #FFFFFF;

    color:
        #17121A !important;

    border:
        3px solid #17121A;

    border-radius:
        22px;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        13px;

    line-height:
        1.3;

    text-align:
        center;

    transform:
        rotate(4deg);

    box-shadow:
        6px 6px 0 #FF2F88;
}


/* ==========================================================
   NOTEBOOK
   ========================================================== */

.notebook {

    padding:
        17px;

    background:
        #FFF1C7;

    border:
        2px solid #18131A;

    border-radius:
        5px;

    box-shadow:
        7px 8px 0 #000;

    transform:
        rotate(.4deg);
}


.notebook-title {

    color:
        #18131A !important;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        18px;

    border-bottom:
        2px dashed #18131A;

    padding-bottom:
        7px;
}


/* ==========================================================
   PIPELINE
   ========================================================== */

.pipeline-heading {

    margin-top:
        24px;

    margin-bottom:
        12px;

    color:
        #FFFFFF !important;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        18px;
}


.pipe {

    min-height:
        108px;

    padding:
        12px;

    border:
        2px solid #18131A;

    border-radius:
        8px;

    box-shadow:
        4px 5px 0 #000;
}


.pipe-yellow {
    background:#FFD42E;
}


.pipe-pink {
    background:#FF4A98;
}


.pipe-cyan {
    background:#2DE4DF;
}


.pipe-green {
    background:#B9EF3D;
}


.pipe-red {
    background:#FF6848;
}


.pipe-number {

    color:
        #18131A !important;

    font-size:
        9px;

    font-weight:
        950;
}


.pipe-name {

    margin-top:
        4px;

    color:
        #18131A !important;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        16px;
}


.pipe-copy {

    margin-top:
        5px;

    color:
        #211921 !important;

    font-size:
        10px;

    line-height:
        1.35;

    font-weight:
        800;
}


/* ==========================================================
   BUILDER
   ========================================================== */

.builder-panel {

    padding:
        18px;

    border:
        1px solid #413255;

    border-radius:
        15px;

    background:
        #0F0B17;

    box-shadow:
        inset 0 0 35px rgba(112,48,255,.05);
}


.builder-label {

    color:
        #2FE7FF !important;

    font-size:
        9px;

    font-weight:
        900;

    letter-spacing:
        2px;

    text-transform:
        uppercase;
}


.builder-title {

    margin-top:
        4px;

    color:
        #FFFFFF !important;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        34px;
}


.builder-copy {

    margin-top:
        4px;

    color:
        #978CA2 !important;

    font-size:
        11px;

    line-height:
        1.55;
}


/* ==========================================================
   SECTION TITLES
   ========================================================== */

.section-title {

    margin-top:
        20px;

    margin-bottom:
        8px;

    color:
        #FFFFFF !important;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        17px;
}


/* ==========================================================
   CONSOLE
   ========================================================== */

.console {

    min-height:
        275px;

    padding:
        15px;

    background:
        #06100D;

    border:
        2px solid #293C35;

    border-radius:
        12px;

    box-shadow:
        inset 0 0 35px rgba(0,255,150,.05);
}


.console-title {

    color:
        #3EFFAA !important;

    font-family:
        Consolas,
        monospace !important;

    font-size:
        10px;

    font-weight:
        900;
}


.console-line {

    color:
        #6DDFB2 !important;

    font-family:
        Consolas,
        monospace !important;

    font-size:
        10px;

    line-height:
        1.85;
}


/* ==========================================================
   LAB
   ========================================================== */

.lab {

    padding:
        6px;

    background:
        #0F0F20;

    border:
        2px solid #38345A;

    border-radius:
        12px;

    overflow:
        hidden;
}


/* ==========================================================
   STATS
   ========================================================== */

.stat {

    margin-bottom:
        10px;

    padding:
        12px;

    background:
        #FFF1C7;

    border:
        2px solid #18131A;

    border-radius:
        8px;

    box-shadow:
        4px 4px 0 #000;
}


.stat-value {

    color:
        #18131A !important;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        29px;
}


.stat-label {

    color:
        #574D54 !important;

    font-size:
        9px;

    font-weight:
        900;

    letter-spacing:
        1px;
}


/* ==========================================================
   ACTIVITY
   ========================================================== */

.activity {

    padding:
        15px;

    background:
        #FFF1C7;

    border:
        2px solid #18131A;

    border-radius:
        5px;

    box-shadow:
        5px 6px 0 #000;

    transform:
        rotate(-.45deg);
}


.activity-title {

    color:
        #18131A !important;

    font-family:
        "Permanent Marker",
        cursive !important;

    font-size:
        18px;

    border-bottom:
        2px dashed #18131A;

    padding-bottom:
        7px;
}


.activity-row {

    padding:
        9px 0;

    color:
        #292128 !important;

    font-size:
        10px;

    font-weight:
        800;

    border-bottom:
        1px dashed #C4AC6D;
}


/* ==========================================================
   RESULT
   ========================================================== */

.result {

    padding:
        18px;

    background:
        linear-gradient(
            135deg,
            #180F2D,
            #0B1427
        );

    border:
        1px solid #4D3868;

    border-radius:
        15px;

    box-shadow:
        0 14px 36px rgba(0,0,0,.25);
}


.result-title {

    color:
        #2FE7FF !important;

    font-family:
        "Bangers",
        Impact,
        sans-serif !important;

    font-size:
        32px;
}


/* ==========================================================
   INPUTS
   ========================================================== */

.stTextArea textarea {

    background:
        #FFF9E8 !important;

    color:
        #1B1520 !important;

    border:
        2px solid #18131A !important;

    border-radius:
        7px !important;

    font-size:
        13px !important;

    font-weight:
        700 !important;
}


.stTextInput input {

    background:
        #FFF9E8 !important;

    color:
        #1B1520 !important;

    border:
        2px solid #18131A !important;

    border-radius:
        7px !important;

    font-weight:
        700 !important;
}


/* ==========================================================
   BUTTONS
   ========================================================== */

.stButton > button {

    min-height:
        45px !important;

    border-radius:
        9px !important;

    font-weight:
        950 !important;
}


.stButton > button[kind="primary"] {

    background:
        linear-gradient(
            135deg,
            #FF5833,
            #FF2F88
        ) !important;

    color:
        #FFFFFF !important;

    border:
        1px solid #FF87B7 !important;

    box-shadow:
        4px 5px 0 #17111B !important;
}


.stButton > button[kind="secondary"] {

    background:
        linear-gradient(
            135deg,
            #FF5833,
            #FF2F88
        ) !important;

    color:
        #FFFFFF !important;

    border:
        1px solid #FF87B7 !important;

    box-shadow:
        4px 5px 0 #17111B !important;
}


/* ==========================================================
   TABS
   ========================================================== */

button[data-baseweb="tab"] {

    color:
        #A9A0B4 !important;

    font-size:
        11px !important;

    font-weight:
        900 !important;
}


button[data-baseweb="tab"][aria-selected="true"] {

    color:
        #FFFFFF !important;
}


/* ==========================================================
   EXPANDERS
   ========================================================== */

[data-testid="stExpander"] {

    background:
        #100D17 !important;

    border:
        1px solid #3D324A !important;

    border-radius:
        10px !important;
}


/* ==========================================================
   FOOTER
   ========================================================== */

.footer {

    text-align:
        center;

    color:
        #645A6D !important;

    font-size:
        9px;

    font-weight:
        900;

    letter-spacing:
        2px;
}

</style>
"""
)


# ============================================================
# SIDEBAR — AGENT CONTROL DECK
# ============================================================

with st.sidebar:

    html(
    """
    <div class="sidebar-brand">
        AGENT<span>FORGE</span>
    </div>

    <div class="sidebar-sub">
        AGENT CONTROL DECK
    </div>
    """
    )


    # --------------------------------------------------------
    # CURRENT MISSION
    # --------------------------------------------------------

    mission_preview = (
        st.session_state.mission.strip()
    )

    if not mission_preview:

        mission_preview = (
            "No mission loaded."
        )

    if len(mission_preview) > 105:

        mission_preview = (
            mission_preview[:102]
            + "..."
        )

    html(
    f"""
    <div class="sidebar-card">

        <div class="sidebar-label">
            CURRENT MISSION
        </div>

        <div class="sidebar-value">
            {mission_preview}
        </div>

    </div>
    """
    )


    # --------------------------------------------------------
    # ENGINE STATUS
    # --------------------------------------------------------

    if backend_is_online():

        html(
        """
        <div class="sidebar-status">

            <div class="sidebar-label">
                ENGINE STATUS
            </div>

            <div class="online">
                ● ONLINE
            </div>

            <div style="
                color:#8E839A;
                font-size:9px;
            ">
                FastAPI + Gemini
            </div>

        </div>
        """
        )

    else:

        html(
        """
        <div class="sidebar-status">

            <div class="sidebar-label">
                ENGINE STATUS
            </div>

            <div class="offline">
                ● OFFLINE
            </div>

            <div style="
                color:#8E839A;
                font-size:9px;
            ">
                Start FastAPI to execute missions
            </div>

        </div>
        """
        )


    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    html(
    """
    <div style="
        margin-top:16px;
        color:#83778E;
        font-size:8px;
        font-weight:900;
        letter-spacing:2px;
    ">
        MODEL
    </div>

    <div style="
        color:#FFFFFF;
        font-size:12px;
        font-weight:900;
        margin-top:5px;
    ">
        ✦ Gemini
    </div>
    """
    )


    # --------------------------------------------------------
    # TOOL CONSOLE
    # --------------------------------------------------------

    html(
    """
    <div style="
        margin-top:18px;
        color:#83778E;
        font-size:8px;
        font-weight:900;
        letter-spacing:2px;
    ">
        TOOL CONSOLE
    </div>

    <div style="
        color:#90859D;
        font-size:9px;
        line-height:1.45;
        margin-top:4px;
        margin-bottom:7px;
    ">
        Run individual AgentForge tools directly.
    </div>
    """
    )


    tool_choice = st.selectbox(
        "Tool",
        [
            "🔎 Search Catalog",
            "🧮 Calculator",
            "📊 Compare Catalog",
            "📚 Search Docs",
        ],
        key="sidebar_tool_choice",
        label_visibility="collapsed",
    )


    if tool_choice == "🔎 Search Catalog":

        query = st.text_input(
            "Search query",
            placeholder="laptop",
            key="sidebar_search_query",
        )

        tool_name = "search_catalog"

        tool_arguments = {
            "query": query,
        }


    elif tool_choice == "🧮 Calculator":

        expression = st.text_input(
            "Expression",
            placeholder="80000 * 0.18",
            key="sidebar_calculator_expression",
        )

        tool_name = "calculator"

        tool_arguments = {
            "expression": expression,
        }


    elif tool_choice == "📊 Compare Catalog":

        budget = st.number_input(
            "Budget",
            min_value=0,
            value=int(
                st.session_state.sidebar_compare_budget
            ),
            step=5000,
            key="sidebar_compare_budget",
        )

        tool_name = "compare_catalog"

        tool_arguments = {
            "budget": budget,
        }


    else:

        query = st.text_input(
            "Documentation query",
            placeholder="timeout",
            key="sidebar_docs_query",
        )

        tool_name = "search_docs"

        tool_arguments = {
            "query": query,
        }


    # --------------------------------------------------------
    # RUN TOOL
    # --------------------------------------------------------

    run_tool = st.button(
        "▶ RUN TOOL",
        type="primary",
        use_container_width=True,
        key="sidebar_run_tool",
    )


    if run_tool:

        valid = True


        if tool_name in {
            "search_catalog",
            "search_docs",
        }:

            if not tool_arguments["query"].strip():

                st.warning(
                    "Enter a query first."
                )

                valid = False


        elif tool_name == "calculator":

            if not tool_arguments["expression"].strip():

                st.warning(
                    "Enter an expression first."
                )

                valid = False


        if valid:

            try:

                with st.spinner(
                    "Running tool..."
                ):

                    tool_result = execute_tool(
                        tool_name,
                        tool_arguments,
                    )

                st.session_state.sidebar_tool_result = (
                    tool_result
                )

            except Exception as exc:

                st.session_state.sidebar_tool_result = None

                st.error(
                    f"Tool failed: {exc}"
                )


    # --------------------------------------------------------
    # TOOL OUTPUT
    # --------------------------------------------------------

    if (
        st.session_state.sidebar_tool_result
        is not None
    ):

        html(
        """
        <div style="
            margin-top:10px;
            padding-top:10px;
            border-top:1px solid #30243E;
        ">

            <div class="sidebar-label">
                TOOL OUTPUT
            </div>

        </div>
        """
        )

        render_sidebar_tool_result(
            st.session_state.sidebar_tool_result
        )


    # --------------------------------------------------------
    # LAST RUN
    # --------------------------------------------------------

    result = st.session_state.result

    last_score = 0
    last_tools = 0
    last_failures = 0

    if result:

        evaluation = result.get(
            "evaluation",
            {},
        )

        last_score = evaluation.get(
            "final_score",
            0,
        )

        last_tools = evaluation.get(
            "tool_calls",
            0,
        )

        last_failures = evaluation.get(
            "failures",
            0,
        )


    html(
    f"""
    <div style="
        border-top:1px solid #30243E;
        margin-top:16px;
        padding-top:14px;
    ">

        <div class="sidebar-label">
            LAST RUN
        </div>

        <div style="
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:6px;
            margin-top:8px;
        ">

            <div style="
                background:#15101F;
                border:1px solid #342846;
                border-radius:8px;
                padding:8px 4px;
                text-align:center;
            ">

                <div style="
                    color:#2FE7FF;
                    font-family:'Bangers',Impact,sans-serif;
                    font-size:21px;
                ">
                    {last_score}
                </div>

                <div style="
                    color:#7D7289;
                    font-size:7px;
                    font-weight:900;
                ">
                    SCORE
                </div>

            </div>


            <div style="
                background:#15101F;
                border:1px solid #342846;
                border-radius:8px;
                padding:8px 4px;
                text-align:center;
            ">

                <div style="
                    color:#FF5F9B;
                    font-family:'Bangers',Impact,sans-serif;
                    font-size:21px;
                ">
                    {last_tools}
                </div>

                <div style="
                    color:#7D7289;
                    font-size:7px;
                    font-weight:900;
                ">
                    TOOLS
                </div>

            </div>


            <div style="
                background:#15101F;
                border:1px solid #342846;
                border-radius:8px;
                padding:8px 4px;
                text-align:center;
            ">

                <div style="
                    color:#B8EF3D;
                    font-family:'Bangers',Impact,sans-serif;
                    font-size:21px;
                ">
                    {last_failures}
                </div>

                <div style="
                    color:#7D7289;
                    font-size:7px;
                    font-weight:900;
                ">
                    FAILURES
                </div>

            </div>


            <div style="
                background:#15101F;
                border:1px solid #342846;
                border-radius:8px;
                padding:8px 4px;
                text-align:center;
            ">

                <div style="
                    color:#FFD42E;
                    font-family:'Bangers',Impact,sans-serif;
                    font-size:21px;
                ">
                    {st.session_state.missions_run}
                </div>

                <div style="
                    color:#7D7289;
                    font-size:7px;
                    font-weight:900;
                ">
                    RUNS
                </div>

            </div>

        </div>

    </div>
    """
    )


    # --------------------------------------------------------
    # QUICK ACTIONS
    # --------------------------------------------------------

    st.write("")

    html(
    """
    <div class="sidebar-label"
         style="margin-bottom:7px;">
        QUICK ACTIONS
    </div>
    """
    )


    st.button(
        "＋ NEW MISSION",
        key="sidebar_new_mission",
        use_container_width=True,
        on_click=new_mission,
    )


    run_again = st.button(
        "↻ RUN AGAIN",
        key="sidebar_run_again",
        disabled=not bool(
            st.session_state.mission.strip()
        ),
        use_container_width=True,
    )


    st.button(
        "× CLEAR RUN",
        key="sidebar_clear_run",
        disabled=st.session_state.result is None,
        use_container_width=True,
        on_click=clear_current_run,
    )


    if run_again:

        execute_mission(
            st.session_state.mission
        )


    html(
    """
    <div class="motto">
        BUILD<br>
        <span class="motto-pink">BREAK</span><br>
        <span class="motto-cyan">MAKE IT</span><br>
        BETTER!
    </div>
    """
    )


# ============================================================
# TOP COMMAND BAR
# ============================================================

top1, top2, top3 = st.columns(
    [1.1, 4.5, .8],
    vertical_alignment="center",
)


with top1:

    html(
    """
    <div class="brand">
        ⚒ AGENTFORGE
    </div>
    """
    )


with top2:

    html(
    """
    <div class="search-box">
        What mission shall we give the agent today?
    </div>
    """
    )


with top3:

    html(
    """
    <div class="gemini-pill">
        ✦ GEMINI
    </div>
    """
    )


# ============================================================
# NAVIGATION
# ============================================================

(
    launch_tab,
    builder_tab,
    process_tab,
    chaos_tab,
    evaluation_tab,
    settings_tab,
) = st.tabs(
    [
        "🚀 LAUNCH PAD",
        "🎯 MISSION BUILDER",
        "◈ LIVE PROCESS",
        "🧪 CHAOS LAB",
        "🏆 EVALUATION",
        "⚙️ SETTINGS",
    ]
)


# ============================================================
# LAUNCH PAD
# ============================================================

with launch_tab:

    st.write("")


    # --------------------------------------------------------
    # HERO
    # --------------------------------------------------------

    html(
    f"""
    <div class="hero">

        <div class="hero-dots"></div>

        <div class="hero-copy">

            <div class="kicker">
                BUILD • RUN • OBSERVE • BREAK • EVALUATE
            </div>

            <div class="hero-title">
                FORGE<br>
                <span class="hero-pink">
                    INTELLIGENT
                </span><br>
                <span class="hero-cyan">
                    AGENTS
                </span>
            </div>

            <div class="hero-description">
                Give an agent a mission.
                Watch it plan, act, recover and prove
                what it can actually do.
            </div>

        </div>

        <div class="hero-robot">

            <img
                src="data:image/png;base64,{MASCOT_B64}"
                alt="AgentForge AI Agent"
            >

        </div>

        <div class="speech">
            HEY!<br>
            I'm ready for<br>
            your mission!
        </div>

    </div>
    """
    )


    # --------------------------------------------------------
    # MISSION
    # --------------------------------------------------------

    st.write("")

    mission_col, action_col = st.columns(
        [1.8, .55],
        gap="medium",
    )


    with mission_col:

        html(
        """
        <div class="notebook">

            <div class="notebook-title">
                🎯 MISSION OBJECTIVE
            </div>

        </div>
        """
        )

        mission = st.text_area(
            "Mission",
            height=135,
            label_visibility="collapsed",
            key="main_mission",
        )

        st.session_state.mission = mission


    with action_col:

        st.write("")

        launch = st.button(
            "🚀 LAUNCH",
            type="primary",
            use_container_width=True,
            key="main_launch",
        )

        st.button(
            "✨ EXAMPLE",
            type="secondary",
            use_container_width=True,
            key="main_example",
            on_click=set_example_mission,
        )


    if launch:

        execute_mission(
            mission
        )


    # --------------------------------------------------------
    # PIPELINE
    # --------------------------------------------------------

    html(
    """
    <div class="pipeline-heading">
        THE AGENT PIPELINE
    </div>
    """
    )


    pipeline_columns = st.columns(
        5,
        gap="small",
    )


    pipeline_data = [
        (
            "pipe-yellow",
            "01",
            "PLAN",
            "Break the mission into useful steps.",
        ),
        (
            "pipe-pink",
            "02",
            "ACT",
            "Choose and use the right tools.",
        ),
        (
            "pipe-cyan",
            "03",
            "OBSERVE",
            "Inspect returned evidence.",
        ),
        (
            "pipe-green",
            "04",
            "RECOVER",
            "Handle failures and continue.",
        ),
        (
            "pipe-red",
            "05",
            "EVALUATE",
            "Measure final performance.",
        ),
    ]


    for column, data in zip(
        pipeline_columns,
        pipeline_data,
    ):

        css_class, number, name, description = data

        with column:

            html(
            f"""
            <div class="pipe {css_class}">

                <div class="pipe-number">
                    {number}
                </div>

                <div class="pipe-name">
                    {name}
                </div>

                <div class="pipe-copy">
                    {description}
                </div>

            </div>
            """
            )


    # --------------------------------------------------------
    # WORKSPACE
    # --------------------------------------------------------

    st.write("")

    console_col, lab_col, stats_col = st.columns(
        [1, 1.2, .65],
        gap="medium",
    )


    with console_col:

        html(
        """
        <div class="section-title">
            🖥 MISSION CONSOLE
        </div>
        """
        )

        lines = [
            "AgentForge Core initialized...",
            "Tool system connected...",
            "Environment loaded...",
        ]

        result = st.session_state.result

        if result:

            lines.append(
                "Mission received..."
            )

            for step in result.get(
                "steps",
                [],
            ):

                lines.append(
                    f"{step.get('tool','unknown')}"
                    f" → "
                    f"{step.get('status','unknown')}"
                )

            lines.append(
                "Evaluator completed."
            )

            lines.append(
                "Mission report ready."
            )

        else:

            lines.append(
                "Waiting for mission..."
            )

        html(
        """
        <div class="console">

            <div class="console-title">
                AGENTFORGE://MISSION_CONSOLE
            </div>
        """
        +
        "".join(
            f"""
            <div class="console-line">
                &gt; {line}
            </div>
            """
            for line in lines
        )
        +
        """
        </div>
        """
        )


    with lab_col:

        html(
        """
        <div class="section-title">
            🧪 LAB ENVIRONMENT
        </div>
        """
        )

        if LAB is not None:

            html(
            """
            <div class="lab">
            """
            )

            st.image(
                LAB,
                width="stretch",
            )

            html(
            """
            </div>
            """
            )

        else:

            st.warning(
                "Lab artwork not found."
            )


    with stats_col:

        html(
        """
        <div class="section-title">
            📈 QUICK STATS
        </div>
        """
        )

        result = st.session_state.result

        tools = 0
        score = 0
        failures = 0
        success_rate = 0

        if result:

            evaluation = result.get(
                "evaluation",
                {},
            )

            tools = evaluation.get(
                "tool_calls",
                0,
            )

            score = evaluation.get(
                "final_score",
                0,
            )

            failures = evaluation.get(
                "failures",
                0,
            )

            success_rate = evaluation.get(
                "task_completion",
                0,
            )

        html(
        f"""
        <div class="stat">

            <div class="stat-value">
                {success_rate}%
            </div>

            <div class="stat-label">
                SUCCESS
            </div>

        </div>

        <div class="stat">

            <div class="stat-value">
                {tools}
            </div>

            <div class="stat-label">
                TOOLS
            </div>

        </div>

        <div class="stat">

            <div class="stat-value">
                {score}
            </div>

            <div class="stat-label">
                SCORE
            </div>

        </div>

        <div class="stat">

            <div class="stat-value">
                {failures}
            </div>

            <div class="stat-label">
                FAILURES
            </div>

        </div>
        """
        )


    # --------------------------------------------------------
    # ACTIVITY / RESULT
    # --------------------------------------------------------

    st.write("")

    activity_col, result_col = st.columns(
        [.7, 1.3],
        gap="medium",
    )


    with activity_col:

        html(
        """
        <div class="activity">

            <div class="activity-title">
                ⚡ ACTIVITY FEED
            </div>

            <div class="activity-row">
                🤖 Agent core ready
            </div>

            <div class="activity-row">
                🔧 Tool system connected
            </div>

            <div class="activity-row">
                🧪 Environment loaded
            </div>

            <div class="activity-row">
                ⏱ Waiting for mission...
            </div>

        </div>
        """
        )


    with result_col:

        result = st.session_state.result

        if result:

            html(
            """
            <div class="result">

                <div class="result-title">
                    🏆 MISSION COMPLETE
                </div>

            </div>
            """
            )

            st.write(
                result.get(
                    "final_answer",
                    "No final answer returned.",
                )
            )

            st.caption(
                "Run ID: "
                + str(
                    result.get(
                        "run_id",
                        "—",
                    )
                )
            )

        else:

            html(
            """
            <div class="activity">

                <div class="activity-title">
                    💡 READY FOR ORDERS
                </div>

                <div class="activity-row">
                    Give AgentForge a mission.
                </div>

                <div class="activity-row">
                    The agent will plan, act,
                    observe, recover and evaluate.
                </div>

            </div>
            """
            )


# ============================================================
# MISSION BUILDER
# ============================================================

with builder_tab:

    st.write("")


    html(
    """
    <div class="builder-panel">

        <div class="builder-label">
            MISSION BUILDER
        </div>

        <div class="builder-title">
            DESIGN THE RUN.
        </div>

        <div class="builder-copy">
            Configure the mission before sending
            the agent into the Forge.
        </div>

    </div>
    """
    )

    st.write("")


    builder_left, builder_right = st.columns(
        [1.35, .75],
        gap="medium",
    )


    with builder_left:

        html(
        """
        <div class="notebook">

            <div class="notebook-title">
                🎯 DEFINE THE MISSION
            </div>

        </div>
        """
        )

        builder_mission = st.text_area(
            "Builder Mission",
            height=220,
            label_visibility="collapsed",
            key="builder_mission",
        )


    with builder_right:

        with st.container(border=True):

            st.markdown(
                "### ⚙️ Agent Configuration"
            )

            model = st.selectbox(
                "Model",
                ["Gemini"],
                index=0,
                key="builder_model_select",
            )

            max_steps = st.slider(
                "Maximum steps",
                min_value=1,
                max_value=5,
                value=st.session_state.builder_steps,
                key="builder_steps_select",
            )

            chaos = st.toggle(
                "Enable Chaos Mode",
                value=st.session_state.builder_chaos,
                key="builder_chaos_toggle",
            )

            failure_options = [
                "Tool timeout",
                "Invalid tool response",
                "Conflicting evidence",
            ]

            current_failure = (
                st.session_state.builder_failure
                if st.session_state.builder_failure
                in failure_options
                else "Tool timeout"
            )

            failure = st.selectbox(
                "Failure scenario",
                failure_options,
                index=failure_options.index(
                    current_failure
                ),
                disabled=not chaos,
                key="builder_failure_select",
            )

            st.session_state.builder_model = model
            st.session_state.builder_steps = max_steps
            st.session_state.builder_chaos = chaos
            st.session_state.builder_failure = failure

            st.write("")

            build_launch = st.button(
                "🚀 BUILD & LAUNCH",
                type="primary",
                use_container_width=True,
                key="builder_launch",
            )

            save_config = st.button(
                "💾 SAVE CONFIGURATION",
                type="secondary",
                use_container_width=True,
                key="builder_save",
            )


            if save_config:

                mission_to_save = (
                    builder_mission.strip()
                )

                st.session_state.mission = (
                    mission_to_save
                )

                st.success(
                    "Configuration saved for this session."
                )


            if build_launch:

                mission_to_run = (
                    builder_mission.strip()
                )

                if not mission_to_run:

                    st.error(
                        "Enter a mission before launching."
                    )

                else:

                    st.session_state.mission = (
                        mission_to_run
                    )

                    st.session_state.main_mission = (
                        mission_to_run
                    )

                    execute_mission(
                        mission_to_run,
                        chaos_mode=chaos,
                        chaos_type=failure,
                    )


    # --------------------------------------------------------
    # CONFIGURATION SNAPSHOT
    # --------------------------------------------------------

    st.write("")

    html(
    """
    <div class="pipeline-heading">
        CONFIGURATION SNAPSHOT
    </div>
    """
    )


    config_columns = st.columns(
        4,
        gap="small",
    )


    config_data = [
        (
            "MODEL",
            st.session_state.builder_model,
        ),
        (
            "MAX STEPS",
            str(
                st.session_state.builder_steps
            ),
        ),
        (
            "CHAOS",
            "ON"
            if st.session_state.builder_chaos
            else "OFF",
        ),
        (
            "FAILURE",
            st.session_state.builder_failure
            if st.session_state.builder_chaos
            else "NONE",
        ),
    ]


    for column, (
        title,
        value,
    ) in zip(
        config_columns,
        config_data,
    ):

        with column:

            html(
            f"""
            <div class="stat">

                <div class="stat-value"
                     style="font-size:18px;">
                    {value}
                </div>

                <div class="stat-label">
                    {title}
                </div>

            </div>
            """
            )


    # --------------------------------------------------------
    # MISSION RESULT
    # --------------------------------------------------------

    builder_result = st.session_state.result

    if builder_result:

        builder_evaluation = (
            builder_result.get(
                "evaluation",
                {},
            )
        )

        st.write("")

        html(
        """
        <div class="pipeline-heading">
            🏆 MISSION RESULT
        </div>
        """
        )

        result_metrics = st.columns(
            4,
            gap="small",
        )


        with result_metrics[0]:

            st.metric(
                "FINAL SCORE",
                builder_evaluation.get(
                    "final_score",
                    0,
                ),
            )


        with result_metrics[1]:

            st.metric(
                "COMPLETION",
                f"{builder_evaluation.get('task_completion', 0)}%",
            )


        with result_metrics[2]:

            st.metric(
                "TOOLS",
                builder_evaluation.get(
                    "tool_calls",
                    0,
                ),
            )


        with result_metrics[3]:

            st.metric(
                "FAILURES",
                builder_evaluation.get(
                    "failures",
                    0,
                ),
            )


        st.write("")

        html(
        """
        <div class="result">

            <div class="result-title">
                🏆 MISSION COMPLETE
            </div>

        </div>
        """
        )

        st.write(
            builder_result.get(
                "final_answer",
                "No final answer returned.",
            )
        )

        if builder_result.get(
            "run_id"
        ):

            st.caption(
                "Run ID: "
                + str(
                    builder_result["run_id"]
                )
            )


# ============================================================
# LIVE PROCESS
# ============================================================

with process_tab:

    st.write("")

    html(
    """
    <div class="builder-panel">

        <div class="builder-label">
            LIVE PROCESS
        </div>

        <div class="builder-title">
            WATCH THE AGENT WORK.
        </div>

        <div class="builder-copy">
            Inspect planning, tool execution,
            recovery and finalization.
        </div>

    </div>
    """
    )

    st.write("")

    result = st.session_state.result

    if result is None:

        st.info(
            "Launch a mission to populate the live trace."
        )

    else:

        evaluation = result.get(
            "evaluation",
            {},
        )

        a, b, c, d = st.columns(4)


        with a:

            st.metric(
                "RUN ID",
                result.get(
                    "run_id",
                    "—",
                )[-8:],
            )


        with b:

            st.metric(
                "TOOL CALLS",
                evaluation.get(
                    "tool_calls",
                    0,
                ),
            )


        with c:

            st.metric(
                "FAILURES",
                evaluation.get(
                    "failures",
                    0,
                ),
            )


        with d:

            st.metric(
                "SCORE",
                evaluation.get(
                    "final_score",
                    0,
                ),
            )


        st.write("")

        trace = result.get(
            "trace",
            [],
        )

        if not trace:

            st.info(
                "No execution trace returned."
            )

        else:

            for index, event in enumerate(
                trace,
                start=1,
            ):

                stage = event.get(
                    "stage",
                    "execution",
                )

                status = event.get(
                    "status",
                    "unknown",
                )

                icon_map = {
                    "mission": "🎯",
                    "planner": "🧠",
                    "recovery": "🔧",
                    "finalizer": "✍️",
                    "evaluator": "🏆",
                }

                icon = icon_map.get(
                    stage,
                    "⚙️",
                )

                with st.expander(
                    f"{icon} STEP {index} · "
                    f"{stage.upper()} · "
                    f"{status.upper()}",
                    expanded=index <= 2,
                ):

                    st.json(
                        event
                    )

        if result.get(
            "trace_path"
        ):

            st.caption(
                f"Saved trace: {result['trace_path']}"
            )


# ============================================================
# CHAOS LAB
# ============================================================

with chaos_tab:

    st.write("")

    left, right = st.columns(
        [1.05, .95],
        gap="medium",
    )


    with left:

        html(
        """
        <div class="hero">

            <div class="hero-dots"></div>

            <div class="hero-copy">

                <div class="kicker">
                    CONTROLLED FAILURE TESTING
                </div>

                <div class="hero-title">
                    BREAK<br>
                    <span class="hero-pink">
                        THE AGENT
                    </span>
                </div>

                <div class="hero-description">
                    Inject a controlled failure and
                    see whether the agent can recover.
                </div>

            </div>

        </div>
        """
        )


    with right:

        with st.container(border=True):

            st.markdown(
                "### 🧪 Failure Lab"
            )

            chaos_task = st.text_area(
                "Chaos Mission",
                height=155,
                label_visibility="collapsed",
                key="chaos_task",
            )

            chaos_failure_options = [
                "Tool timeout",
                "Invalid tool response",
                "Conflicting evidence",
            ]

            chaos_failure = st.selectbox(
                "Failure scenario",
                chaos_failure_options,
                index=chaos_failure_options.index(
                    st.session_state.chaos_failure
                    if st.session_state.chaos_failure
                    in chaos_failure_options
                    else "Tool timeout"
                ),
                key="chaos_failure",
            )

            chaos_launch = st.button(
                "💥 BREAK THE AGENT",
                type="primary",
                use_container_width=True,
                key="chaos_launch",
            )

            if chaos_launch:

                result = execute_mission(
                    chaos_task,
                    chaos_mode=True,
                    chaos_type=chaos_failure,
                )

                if result:

                    st.success(
                        f"Injected: {chaos_failure}"
                    )


    st.write("")

    result = st.session_state.result

    if result:

        evaluation = result.get(
            "evaluation",
            {},
        )

        failures = evaluation.get(
            "failures",
            0,
        )

        recovery = evaluation.get(
            "recovery",
            0,
        )

        if failures:

            st.warning(
                "💥 Controlled failure detected."
            )

            st.success(
                "🔧 Recovery path recorded."
            )

        else:

            st.info(
                "Current run contains no recorded failure."
            )

        r1, r2, r3 = st.columns(3)


        with r1:

            st.metric(
                "FAILURES",
                failures,
            )


        with r2:

            st.metric(
                "RECOVERY",
                f"{recovery}%",
            )


        with r3:

            st.metric(
                "FINAL SCORE",
                evaluation.get(
                    "final_score",
                    0,
                ),
            )


# ============================================================
# EVALUATION
# ============================================================

with evaluation_tab:

    st.write("")

    html(
    """
    <div class="builder-panel">

        <div class="builder-label">
            AGENT EVALUATION
        </div>

        <div class="builder-title">
            DID IT ACTUALLY WORK?
        </div>

        <div class="builder-copy">
            Measure completion, tool usage,
            reliability, recovery and final quality.
        </div>

    </div>
    """
    )

    st.write("")

    result = st.session_state.result

    if result is None:

        st.info(
            "Launch a mission to generate evaluation data."
        )

    else:

        evaluation = result.get(
            "evaluation",
            {},
        )

        score = evaluation.get(
            "final_score",
            0,
        )

        a, b, c, d = st.columns(4)


        with a:

            st.metric(
                "FINAL SCORE",
                f"{score}/100",
            )


        with b:

            st.metric(
                "COMPLETION",
                f"{evaluation.get('task_completion', 0)}%",
            )


        with c:

            st.metric(
                "TOOLS",
                evaluation.get(
                    "tool_calls",
                    0,
                ),
            )


        with d:

            st.metric(
                "RECOVERY",
                f"{evaluation.get('recovery', 0)}%",
            )


        st.write("")


        if score >= 85:

            st.success(
                "🏆 Excellent agent performance."
            )

        elif score >= 70:

            st.info(
                "✨ Solid performance. There is room to improve."
            )

        else:

            st.warning(
                "🔧 The agent needs improvement."
            )


        st.write("")

        left, right = st.columns(
            [1.15, .85],
            gap="medium",
        )


        with left:

            html(
            """
            <div class="result">

                <div class="result-title">
                    MISSION VERDICT
                </div>

            </div>
            """
            )

            st.write(
                result.get(
                    "final_answer",
                    "No final answer returned.",
                )
            )


        with right:

            if MASCOT is not None:

                st.image(
                    MASCOT,
                    width=300,
                )


# ============================================================
# SETTINGS
# ============================================================

with settings_tab:

    st.write("")

    html(
    """
    <div class="builder-panel">

        <div class="builder-label">
            AGENTFORGE SETTINGS
        </div>

        <div class="builder-title">
            CONTROL THE LAB.
        </div>

        <div class="builder-copy">
            Configure interface and execution preferences.
        </div>

    </div>
    """
    )

    st.write("")


    settings_left, settings_right = st.columns(
        [1, 1],
        gap="medium",
    )


    with settings_left:

        with st.container(border=True):

            st.markdown(
                "### ⚙️ Interface"
            )

            density = st.selectbox(
                "Interface density",
                [
                    "Compact",
                    "Comfortable",
                    "Spacious",
                ],
                index=[
                    "Compact",
                    "Comfortable",
                    "Spacious",
                ].index(
                    st.session_state.theme_density
                ),
                key="settings_density",
            )

            show_console = st.toggle(
                "Show execution console",
                value=st.session_state.show_console,
                key="settings_console",
            )

            st.session_state.theme_density = density
            st.session_state.show_console = show_console

            st.info(
                "AgentForge visual identity remains "
                "locked to the comic laboratory direction."
            )


    with settings_right:

        with st.container(border=True):

            st.markdown(
                "### 🤖 Engine"
            )

            st.write(
                "Provider"
            )

            st.code(
                "Gemini"
            )

            st.write(
                "Backend"
            )

            if backend_is_online():

                st.success(
                    "FastAPI connected"
                )

            else:

                st.error(
                    "FastAPI unavailable"
                )

            st.write(
                "Backend URL"
            )

            st.code(
                BACKEND_URL
            )

            st.write(
                "Available tools"
            )

            st.code(
                "calculator\n"
                "search_catalog\n"
                "compare_catalog\n"
                "search_docs"
            )


    st.write("")

    html(
    """
    <div class="pipeline-heading">
        SESSION
    </div>
    """
    )


    session_cols = st.columns(3)


    with session_cols[0]:

        st.metric(
            "MISSIONS RUN",
            st.session_state.missions_run,
        )


    with session_cols[1]:

        st.metric(
            "MODEL",
            st.session_state.builder_model,
        )


    with session_cols[2]:

        st.metric(
            "ENGINE",
            (
                "ONLINE"
                if backend_is_online()
                else "OFFLINE"
            ),
        )


    st.write("")


    reset_session = st.button(
        "× RESET SESSION",
        type="secondary",
        use_container_width=True,
        key="settings_reset",
    )


    if reset_session:

        for key, value in DEFAULTS.items():

            st.session_state[key] = value

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.write("")

html(
"""
<div class="footer">
    AGENTFORGE · AI AGENT LABORATORY
    · BUILD · RUN · OBSERVE · BREAK · EVALUATE
</div>
"""
)