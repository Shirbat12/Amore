"""
free_text_analysis.py – A-MORE · מודול ניתוח טקסט חופשי
-------------------------------------------------------
Analyzes Hebrew free-text date descriptions using Gemini 2.5 Flash.

Produces:
- personality / interpersonal tags from a closed tag list
- overall sentiment
- warmth_score based on the IPC warmth axis
- agency_score based on the IPC agency axis
- a short summary
- short textual evidence from the original response

Theoretical basis:
The tag set is organized according to the two main IPC axes:
- warmth: warmth, care, listening, responsiveness
- agency: extraversion, confidence, energy, assertiveness

References: Wiggins 1979 · Fletcher et al. 1999 · Reis & Gable 2015
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator


load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Closed tags – organized by IPC axes
# ---------------------------------------------------------------------------

# Warmth axis: positive → negative
_WARMTH_POS = ["חם", "אכפתי", "אותנטי", "כן", "מקשיב", "מתעניין"]
_WARMTH_NEG = ["מרוחק", "קר", "מרוכז בעצמו", "לא מקשיב"]

# Agency axis: positive → negative
_AGENCY_POS = ["דברן", "אנרגטי", "בטוח בעצמו", "תוסס", "מושך"]
_AGENCY_NEG = ["משעמם", "מביך", "שיחה תקועה"]

# Extra positive interpersonal signals
_HUMOR_VIBE = ["מצחיק", "שנון", "קליל"]

# Date/profile-level red flags
_RED_FLAGS = ["פער בין פרופיל למציאות"]

CLOSED_TAGS_HE: List[str] = (
    _WARMTH_POS
    + _WARMTH_NEG
    + _AGENCY_POS
    + _AGENCY_NEG
    + _HUMOR_VIBE
    + _RED_FLAGS
)

TAG_CATEGORY: Dict[str, str] = (
    {tag: "warmth_positive" for tag in _WARMTH_POS}
    | {tag: "warmth_negative" for tag in _WARMTH_NEG}
    | {tag: "agency_positive" for tag in _AGENCY_POS}
    | {tag: "agency_negative" for tag in _AGENCY_NEG}
    | {tag: "humor_vibe" for tag in _HUMOR_VIBE}
    | {tag: "red_flag" for tag in _RED_FLAGS}
)


# ---------------------------------------------------------------------------
# Gemini response schema
# ---------------------------------------------------------------------------

class DateAnalysisResponse(BaseModel):
    tags: List[str] = Field(
        description="עד 4 תגיות מתוך הרשימה הסגורה בלבד, לפי סדר חשיבות יורד",
        max_length=4,
    )
    sentiment: float = Field(
        description="-1 = חוויה שלילית מאוד, 0 = ניטרלי/מעורב, +1 = חיובית מאוד"
    )
    warmth_score: float = Field(
        description="ציון על ציר warmth / IPC: -1 קר מאוד, +1 חם מאוד"
    )
    agency_score: float = Field(
        description="ציון על ציר agency / IPC: -1 פסיבי מאוד, +1 אנרגטי מאוד"
    )
    summary: str = Field(
        description="סיכום עד 2 משפטים בעברית של החוויה"
    )
    evidence: str = Field(
        description="ציטוט קצר מהטקסט המקורי שמסביר את התגית המרכזית"
    )

    @field_validator("sentiment", "warmth_score", "agency_score", mode="before")
    @classmethod
    def clamp_to_range(cls, value: float) -> float:
        """Keep numeric scores inside [-1, 1]."""
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = 0.0

        return max(-1.0, min(1.0, numeric_value))

    @field_validator("tags", mode="before")
    @classmethod
    def deduplicate_limit_and_validate(cls, value) -> List[str]:
        """
        Keep only tags from CLOSED_TAGS_HE, remove duplicates,
        and limit to four tags.
        """
        if not isinstance(value, list):
            return []

        seen = set()
        result = []

        for tag in value:
            tag = str(tag).strip()

            if tag in CLOSED_TAGS_HE and tag not in seen:
                seen.add(tag)
                result.append(tag)

        return result[:4]


# ---------------------------------------------------------------------------
# Few-shot examples
# ---------------------------------------------------------------------------

_FEW_SHOT = """
דוגמאות לניתוח נכון:

טקסט: "היה ממש נחמד, הקשיב לכל מה שאמרתי ושאל שאלות עמוקות. הרגשתי שהוא רוצה לדעת עלי. רק קצת שקט."
תגיות: ["מקשיב", "מתעניין", "כן", "משעמם"]
sentiment: 0.6
warmth_score: 0.9
agency_score: -0.3
evidence: "שאל שאלות עמוקות"

טקסט: "דיבר על עצמו כל הזמן ובכלל לא שאל עלי. היה בטוח בעצמו אבל הרגשתי שקופה."
תגיות: ["בטוח בעצמו", "מרוכז בעצמו", "לא מקשיב", "תוסס"]
sentiment: -0.4
warmth_score: -0.7
agency_score: 0.6
evidence: "בכלל לא שאל עלי"

טקסט: "היה מצחיק ואנרגטי, כיף לשוחח איתו, הזמן עף. הייתי רוצה להיפגש שוב."
תגיות: ["מצחיק", "אנרגטי", "קליל", "תוסס"]
sentiment: 0.85
warmth_score: 0.5
agency_score: 0.8
evidence: "הזמן עף"
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_analysis(text: str = "") -> Dict:
    return {
        "tags": [],
        "sentiment": 0.0,
        "warmth_score": 0.0,
        "agency_score": 0.0,
        "summary": "",
        "evidence": "",
        "raw_text": text,
        "parse_error": False,
    }


def _build_prompt(text: str) -> str:
    tag_list = "\n".join(f"  - {tag}" for tag in CLOSED_TAGS_HE)

    return f"""
אתה מודול NLP של פרויקט A-MORE – מערכת היכרויות מבוססת למידה אישית.
תפקידך הוא לנתח תיאור קצר בעברית של דייט ראשון, ולהחזיר מבנה JSON בלבד.

## רשימת התגיות המותרות
בחר רק מתוך הרשימה הסגורה הבאה:
{tag_list}

## כללי ניתוח
1. בחר עד 4 תגיות בלבד, לפי סדר חשיבות יורד.
2. אל תמציא מידע שלא מופיע בטקסט.
3. sentiment מבטא את החוויה הכוללת של הממלא/ת, לא רק את הצד השני.
4. warmth_score מודד עד כמה הצד השני הרגיש חם, מקשיב, כן ומתעניין.
5. agency_score מודד עד כמה הצד השני הרגיש אנרגטי, יוזם, בטוח ופעיל.
6. summary יהיה עד 2 משפטים בעברית.
7. evidence יהיה מילה או ביטוי ישיר מהטקסט המקורי, לא פרשנות.

{_FEW_SHOT}

## הטקסט לניתוח
{text}
""".strip()


MAX_RETRIES = 3
RETRY_DELAY = 1.5


# ---------------------------------------------------------------------------
# Single text analysis
# ---------------------------------------------------------------------------

def analyze_single_free_text(
    text: str,
    model: str = "gemini-2.5-flash",
    vas_score: Optional[float] = None,
) -> Dict:
    """
    Sends one Hebrew free-text date description to Gemini
    and returns structured NLP analysis.

    vas_score is not sent to Gemini.
    It is only preserved in the output for later validation:
    NLP sentiment/warmth/agency vs. the user's numeric VAS score.
    """
    if text is None or pd.isna(text) or str(text).strip() == "":
        return _empty_analysis("")

    text = str(text).strip()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is missing")
        raise EnvironmentError("GEMINI_API_KEY missing – set it in .env")

    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(text)

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DateAnalysisResponse,
                    temperature=0.1,
                    seed=42,
                ),
            )

            if not response.text:
                raise ValueError("Empty response from Gemini")

            raw = json.loads(response.text.strip())
            validated = DateAnalysisResponse(**raw)

            result = validated.model_dump()
            result["raw_text"] = text
            result["parse_error"] = False

            if vas_score is not None and not pd.isna(vas_score):
                result["vas_score"] = float(vas_score)

            return result

        except Exception as error:
            last_error = error
            logger.warning(
                "Attempt %d/%d failed for text %.40r: %s",
                attempt,
                MAX_RETRIES,
                text,
                error,
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error("Free-text analysis failed after %d attempts: %s", MAX_RETRIES, last_error)

    result = _empty_analysis(text)
    result["parse_error"] = True

    if vas_score is not None and not pd.isna(vas_score):
        result["vas_score"] = float(vas_score)

    return result


# ---------------------------------------------------------------------------
# DataFrame enrichment
# ---------------------------------------------------------------------------

def analyze_free_text_dataframe(
    date_df: pd.DataFrame,
    text_col: str = "free_text",
    vas_col: Optional[str] = "experience_score",
    sleep_seconds: float = 0.3,
    model: str = "gemini-2.5-flash",
) -> pd.DataFrame:
    """
    Adds NLP columns to a date-experience dataframe.

    New columns:
    - nlp_tags
    - nlp_sentiment
    - nlp_warmth
    - nlp_agency
    - nlp_summary
    - nlp_evidence
    - nlp_parse_error

    Note:
    This function should usually run after experiment_analysis
    adds the experience_score column.
    """
    if text_col not in date_df.columns:
        raise ValueError(f"Column '{text_col}' was not found in the dataframe")

    df = date_df.copy()

    texts = df[text_col].fillna("").astype(str).str.strip()

    if vas_col and vas_col in df.columns:
        vas_values = df[vas_col].tolist()
    else:
        vas_values = [None] * len(df)

    analyses = []

    for text, vas in zip(texts, vas_values):
        if not text:
            analyses.append(_empty_analysis(""))
            continue

        analyses.append(
            analyze_single_free_text(
                text=text,
                model=model,
                vas_score=vas,
            )
        )

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    df["nlp_tags"] = [analysis["tags"] for analysis in analyses]
    df["nlp_sentiment"] = [analysis["sentiment"] for analysis in analyses]
    df["nlp_warmth"] = [analysis["warmth_score"] for analysis in analyses]
    df["nlp_agency"] = [analysis["agency_score"] for analysis in analyses]
    df["nlp_summary"] = [analysis["summary"] for analysis in analyses]
    df["nlp_evidence"] = [analysis["evidence"] for analysis in analyses]
    df["nlp_parse_error"] = [analysis["parse_error"] for analysis in analyses]

    return df


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

def summarize_free_text_analysis(date_df: pd.DataFrame) -> Dict:
    """
    Builds a dashboard-ready summary of the NLP analysis.

    Returns a controlled empty response if the dataframe was not enriched yet.
    """
    required_columns = {"nlp_tags", "nlp_sentiment", "nlp_warmth", "nlp_agency"}

    if not required_columns.issubset(date_df.columns):
        return {
            "ready": False,
            "message": "Free text was not analyzed yet",
            "top_nlp_tags": [],
            "avg_nlp_sentiment": None,
            "ipc_center": None,
            "positive_examples": [],
            "negative_examples": [],
            "nlp_insights": [],
        }

    analyzed = date_df[
        date_df["nlp_tags"].apply(lambda tags: isinstance(tags, list) and len(tags) > 0)
    ].copy()

    if analyzed.empty:
        return {
            "ready": False,
            "message": "No analyzed free-text rows yet",
            "top_nlp_tags": [],
            "avg_nlp_sentiment": None,
            "ipc_center": None,
            "positive_examples": [],
            "negative_examples": [],
            "nlp_insights": [],
        }

    all_tags = [
        tag
        for tags in analyzed["nlp_tags"]
        for tag in tags
    ]

    tag_counts = pd.Series(all_tags).value_counts().head(10)

    top_tags = [
        {
            "tag": tag,
            "count": int(count),
            "category": TAG_CATEGORY.get(tag, "unknown"),
        }
        for tag, count in tag_counts.items()
    ]

    avg_sentiment = round(float(analyzed["nlp_sentiment"].mean()), 3)
    avg_warmth = round(float(analyzed["nlp_warmth"].mean()), 3)
    avg_agency = round(float(analyzed["nlp_agency"].mean()), 3)

    def _row_to_example(row: pd.Series) -> Dict:
        return {
            "sentiment": float(row["nlp_sentiment"]),
            "warmth": float(row["nlp_warmth"]),
            "agency": float(row["nlp_agency"]),
            "summary": row["nlp_summary"],
            "tags": row["nlp_tags"],
            "evidence": row.get("nlp_evidence", ""),
        }

    positive_examples = [
        _row_to_example(row)
        for _, row in analyzed.nlargest(3, "nlp_sentiment").iterrows()
    ]

    negative_examples = [
        _row_to_example(row)
        for _, row in analyzed.nsmallest(3, "nlp_sentiment").iterrows()
    ]

    insights = _generate_insights(
        df=analyzed,
        avg_warmth=avg_warmth,
        avg_agency=avg_agency,
        top_tags=top_tags,
    )

    return {
        "ready": True,
        "n_analyzed": int(len(analyzed)),
        "top_nlp_tags": top_tags,
        "avg_nlp_sentiment": avg_sentiment,
        "ipc_center": {
            "warmth": avg_warmth,
            "agency": avg_agency,
        },
        "positive_examples": positive_examples,
        "negative_examples": negative_examples,
        "nlp_insights": insights,
    }


def _generate_insights(
    df: pd.DataFrame,
    avg_warmth: float,
    avg_agency: float,
    top_tags: List[Dict],
) -> List[str]:
    """Generates short Hebrew insights for the dashboard."""
    insights = []
    n_rows = len(df)

    warmth_label = (
        "גבוהה"
        if avg_warmth > 0.3
        else "נמוכה"
        if avg_warmth < -0.3
        else "ממוצעת"
    )

    agency_label = (
        "גבוהה"
        if avg_agency > 0.3
        else "נמוכה"
        if avg_agency < -0.3
        else "ממוצעת"
    )

    insights.append(
        f"על בסיס {n_rows} דייטים עם טקסט חופשי: "
        f"רמת החום הממוצעת היא {warmth_label}, "
        f"ורמת האנרגיה הממוצעת היא {agency_label}."
    )

    if top_tags:
        top = top_tags[0]
        insights.append(
            f"התגית הנפוצה ביותר בטקסטים היא '{top['tag']}' "
            f"({top['count']} מופעים), ומשויכת לקטגוריית {top['category']}."
        )

    red_flag_rows = df["nlp_tags"].apply(
        lambda tags: any(tag in _RED_FLAGS for tag in (tags or []))
    )

    red_flag_percent = int(red_flag_rows.mean() * 100)

    if red_flag_percent > 0:
        insights.append(
            f"ב-{red_flag_percent}% מהדייטים עם טקסט חופשי זוהה פער בין הפרופיל הדיגיטלי למציאות."
        )

    return insights