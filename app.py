import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────
# 데이터 로드
# ────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "data.json"


@st.cache_data
def load_db():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


DB = load_db()
INGREDIENTS = DB["ingredients"]

COUNTRY_LABELS = {"EU": "EU", "US": "미국", "TH": "태국", "CN": "중국"}
STATUS_LABELS = {
    "allowed": "허용",
    "banned": "금지",
    "restricted": "제한",
    "unknown": "미확인",
}
STATUS_COLORS = {
    "allowed": ("#E1F3E6", "#1E7A42"),
    "banned": ("#FBE3E3", "#B93A3A"),
    "restricted": ("#FBF0D4", "#8A6A17"),
    "unknown": ("#FBF0D4", "#8A6A17"),
}


def normalize(name: str) -> str:
    return name.strip().lower()


def find_ingredient(name: str):
    target = normalize(name)
    for item in INGREDIENTS:
        if normalize(item["inci_name"]) == target:
            return item
        for alias in item.get("aliases", []):
            if normalize(alias) == target:
                return item
    return None


def lookup_status(ingredient_name: str, country_code: str):
    item = find_ingredient(ingredient_name)
    if item is None:
        return {
            "status": "unknown",
            "note": "DB에 등록되지 않은 성분입니다. 개별 검토가 필요합니다.",
            "max_concentration": None,
            "matched_name": None,
        }
    country_data = item["countries"].get(country_code)
    if country_data is None:
        return {
            "status": "unknown",
            "note": f"{item['inci_name']}은 DB에 있으나 이 국가 데이터가 없습니다. 개별 검토가 필요합니다.",
            "max_concentration": None,
            "matched_name": item["inci_name"],
        }
    return {
        "status": country_data["status"],
        "note": country_data.get("note", ""),
        "max_concentration": country_data.get("max_concentration"),
        "matched_name": item["inci_name"],
    }


def parse_ingredients(raw: str):
    parts = re.split(r"[,\n]", raw)
    return [p.strip() for p in parts if p.strip()]


# ────────────────────────────────────────────────────────────
# 페이지 설정 & 스타일
# ────────────────────────────────────────────────────────────
st.set_page_config(page_title="성분알리미 — 화장품 성분 규제 사전 확인", page_icon="🧪", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    .hero-band {
        background: #3D5791;
        border-radius: 8px;
        padding: 28px 28px;
        margin-bottom: 24px;
    }
    .hero-band .eyebrow {
        color: rgba(255,255,255,0.85);
        font-size: 0.85rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-weight: 700;
    }
    .hero-band h1 {
        color: #FFFFFF;
        font-weight: 900;
        margin: 6px 0 10px 0;
        font-size: 2rem;
    }
    .hero-band p {
        color: rgba(255,255,255,0.85);
        font-size: 0.95rem;
        line-height: 1.6;
        margin: 4px 0;
    }
    .hero-band p strong { color: #FFFFFF; }

    /* 국가 선택 pills: 기본(미선택) 상태 남색 */
    [data-testid="stPills"] button,
    [data-testid="stPills"] [role="radio"],
    [data-testid="stPills"] [role="checkbox"] {
        border-color: #6E85B5 !important;
        color: #6E85B5 !important;
    }
    /* 국가 선택 pills: 선택 상태 남색 */
    [data-testid="stPills"] [aria-pressed="true"],
    [data-testid="stPills"] [aria-checked="true"] {
        background-color: #3D5791 !important;
        border-color: #3D5791 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stPills"] [aria-pressed="true"] *,
    [data-testid="stPills"] [aria-checked="true"] * {
        color: #FFFFFF !important;
    }
    /* 조회하기 버튼: 배경 남색 + 글자 흰색 */
    button[kind="primary"] {
        background-color: #3D5791 !important;
        border-color: #3D5791 !important;
        color: #FFFFFF !important;
    }
    button[kind="primary"] * {
        color: #FFFFFF !important;
    }

    /* 성분 입력 textarea: 테두리 진한 회색 */
    [data-testid="stTextArea"] textarea,
    [data-testid="stTextArea"] div[data-baseweb="textarea"] {
        border-color: #4B4B4B !important;
    }
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {
        border-color: #4B4B4B !important;
        box-shadow: 0 0 0 1px #4B4B4B !important;
    }

    .detail-item {
        padding: 10px 12px;
        border-radius: 6px;
        border-left: 4px solid transparent;
        margin-bottom: 8px;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .footer-note {
        text-align: center;
        color: #5B6B82;
        font-size: 0.8rem;
        margin-top: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-band">
        <span class="eyebrow">Cosmetic Ingredient Compliance</span>
        <h1>🧪 성분알리미</h1>
        <p>전성분표를 붙여넣고 타겟 국가를 고르면,<br>성분별 규제 현황을 바로 확인합니다.</p>
        <p><strong>국내·해외영업, 전략 마케팅 담당자</strong>를 위한 규제 사전 확인 도구</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────
# 01 국가 선택 (+ 전체 선택 버튼)
# ────────────────────────────────────────────────────────────
country_codes = list(COUNTRY_LABELS.keys())

if "country_selection" not in st.session_state:
    st.session_state.country_selection = []

col_caption, col_btn = st.columns([3, 1])
with col_caption:
    st.markdown("**01 국가 선택**")
    st.caption("조회할 국가를 모두 선택하세요.")
with col_btn:
    all_selected = set(st.session_state.country_selection) == set(country_codes)
    if st.button("전체 해제" if all_selected else "전체 선택", use_container_width=True):
        st.session_state.country_selection = [] if all_selected else country_codes.copy()
        st.rerun()

selected_countries = st.pills(
    "국가 선택",
    options=country_codes,
    format_func=lambda c: COUNTRY_LABELS[c],
    selection_mode="multi",
    label_visibility="collapsed",
    key="country_selection",
)
if selected_countries is None:
    selected_countries = []

# ────────────────────────────────────────────────────────────
# 02 성분 입력
# ────────────────────────────────────────────────────────────
st.markdown("**02 성분 입력**")
st.caption("쉼표(,) 또는 줄바꿈으로 구분해 입력하세요. 전성분표를 그대로 붙여넣어도 됩니다.")

ingredients_raw = st.text_area(
    "성분 입력",
    placeholder="예) Water, Glycerin, Niacinamide, Adenosine, 1,2-Hexanediol",
    height=140,
    label_visibility="collapsed",
)

ingredient_list = parse_ingredients(ingredients_raw)
st.caption(f"인식된 성분 **{len(ingredient_list)}**개")

col1, col2 = st.columns([4, 1])
with col1:
    submit = st.button(
        "조회하기",
        type="primary",
        use_container_width=True,
        disabled=not (selected_countries and ingredient_list),
    )
with col2:
    reset = st.button("🔄", use_container_width=True, help="초기화")

if reset:
    st.session_state.clear()
    st.rerun()

if not (selected_countries and ingredient_list):
    st.caption("국가와 성분을 모두 입력하면 조회할 수 있어요.")

# ────────────────────────────────────────────────────────────
# 결과 렌더링
# ────────────────────────────────────────────────────────────
if submit and selected_countries and ingredient_list:
    st.markdown("---")
    st.subheader("조회 결과")

    legend_html = " &nbsp;&nbsp; ".join(
        f'<span style="color:{STATUS_COLORS[s][1]}">●</span> {STATUS_LABELS[s]}'
        for s in ["allowed", "banned", "unknown"]
    )
    st.markdown(legend_html, unsafe_allow_html=True)

    rows = []
    details = []
    for ing in ingredient_list:
        row = {"성분": ing}
        for code in selected_countries:
            result = lookup_status(ing, code)
            row[COUNTRY_LABELS[code]] = STATUS_LABELS[result["status"]]
            if result["status"] != "allowed":
                details.append({"code": code, "ing": ing, "result": result})
        rows.append(row)

    df = pd.DataFrame(rows).set_index("성분")

    label_to_status = {v: k for k, v in STATUS_LABELS.items()}

    def color_cell(val):
        status = label_to_status.get(val, "unknown")
        bg, fg = STATUS_COLORS[status]
        return f"background-color: {bg}; color: {fg}; font-weight: 700; text-align: center;"

    # pandas 2.1+ 는 applymap 대신 map 사용 (구버전 applymap은 pandas 3.0에서 제거됨)
    styled = df.style.map(color_cell)
    st.dataframe(styled, use_container_width=True)

    st.markdown("#### 세부 사항")
    if not details:
        st.caption("모든 성분이 선택한 국가에서 허용 상태로 확인됐습니다.")
    else:
        for d in details:
            status = d["result"]["status"]
            bg, fg = STATUS_COLORS[status]
            concentration = (
                f" (최대 {d['result']['max_concentration']})"
                if d["result"]["max_concentration"]
                else ""
            )
            note = d["result"]["note"] or ""
            st.markdown(
                f"""
                <div class="detail-item" style="background:{bg}; border-left-color:{fg};">
                    <b>{COUNTRY_LABELS[d['code']]} · {d['ing']}</b><br>
                    <span style="color:{fg}; font-weight:700;">{STATUS_LABELS[status]}{concentration}</span><br>
                    <span style="color:#5B6B82;">{note}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown(
    """
    <div class="footer-note">
        성분알리미 · 화장품 성분 규제 사전 확인 서비스<br>
        조회 결과는 참고용이며, 최종 확인은 전문가 검토를 권장합니다.
    </div>
    """,
    unsafe_allow_html=True,
)
