from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import hashlib

import pandas as pd

from server.models import DateRecord


BASE_DIR = Path(__file__).resolve().parents[2]

BASELINE_PATH = BASE_DIR / "data" / "questionnaire" / "baseline_responses.xlsx"
DATE_EXPERIENCE_PATH = BASE_DIR / "data" / "questionnaire" / "date_experience_responses.xlsx"


def _normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_username(value) -> str:
    return _normalize_text(value).lower()


def _anonymous_user_id(username: str) -> str:
    """
    הופך שם משתמש למזהה אנונימי.
    חשוב כי השאלונים הגיעו מאנשים אמיתיים.
    """
    username = _normalize_username(username)
    return hashlib.sha256(username.encode("utf-8")).hexdigest()[:10]


def _to_number(value, default: float = 0.0) -> float:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return default
    return float(number)


def _split_tags(value) -> List[str]:
    """
    Google Forms מחזיר בחירה מרובה כמחרוזת:
    'טיולים, מוזיקה, ספורט'
    אז נהפוך את זה לרשימה.
    """
    if pd.isna(value):
        return []

    return [
        tag.strip()
        for tag in str(value).split(",")
        if tag.strip()
    ]


def _yes_no_to_bool(value):
    value = _normalize_text(value)

    if value == "כן":
        return True

    if value == "לא":
        return False

    return None


def load_baseline_dataframe(path: Path = BASELINE_PATH) -> pd.DataFrame:
    df = pd.read_excel(path)

    df = df.rename(columns={
        "חותמת זמן": "timestamp",
        "בחירת שם משתמש": "username",
        "כמה דייטים ראשונים חווית בחודש האחרון? (במספרים)": "first_dates_last_month",
        " מתוך הדייטים הראשונים הללו, כמה תורגמו לדייט שני?  (במספרים)": "second_dates_last_month",
        "  מהי רמת השחיקה הכללית שלך כרגע מעולם הדייטינג באפליקציות?  ": "burnout_level",
    })

    df["username_normalized"] = df["username"].apply(_normalize_username)
    df["user_id"] = df["username"].apply(_anonymous_user_id)

    df["first_dates_last_month"] = df["first_dates_last_month"].apply(_to_number)
    df["second_dates_last_month"] = df["second_dates_last_month"].apply(_to_number)
    df["burnout_level"] = df["burnout_level"].apply(_to_number)

    df["second_date_conversion_rate"] = df.apply(
        lambda row: (
            row["second_dates_last_month"] / row["first_dates_last_month"]
            if row["first_dates_last_month"] > 0
            else 0
        ),
        axis=1,
    )

    return df


def load_date_experience_dataframe(path: Path = DATE_EXPERIENCE_PATH) -> pd.DataFrame:
    df = pd.read_excel(path)

    df = df.rename(columns={
        "חותמת זמן": "timestamp",
        "הזנת שם משתמש": "username",
        "  באיזו אפליקציה הכרתם?  ": "dating_app",
        "  מה תחום העיסוק / הקריירה המרכזי שמופיע בפרופיל שלו/ה?  ": "profile_career",
        "  אילו תחומי עניין בלטו בפרופיל שלו/ה? (ניתן לבחור עד 4)  ": "profile_interests",
        '  מה היה ה"ווייב" הויזואלי הדומיננטי של התמונות בפרופיל שלו/ה?  ': "profile_visual_vibe",
        "עד כמה המפגש היה מעניין והשיחה זרמה?": "conversation_flow",
        "  עד כמה האדם שפגשת במציאות תאם לפרופיל ולציפיות שנבנו בצ'אט?  ": "profile_reality_match",
        "   עד כמה הרגשת בנוח ובמרחב בטוח להיות עצמך?  ": "comfort_safety",
        "האם הרגשת ניצוץ או משיכה רומנטית/פיזית ראשונית?": "spark",
        "על מה בעיקר דיברתם? (ניתן לבחור עד 3 תגיות)": "conversation_topics",
        " איך היית מתאר/ת את הדינמיקה הכללית במפגש? (ניתן לבחור עד 3 תגיות)  ": "date_dynamic_tags",
        "בשורה התחתונה, האם תרצה/י לצאת איתו/איתה לדייט שני? ": "second_date",
        " ספר/י לנו במילים שלך איך הייתה חווית הדייט ועל הבן אדם? (משפט או שניים).  ": "free_text",
    })

    df["username_normalized"] = df["username"].apply(_normalize_username)
    df["user_id"] = df["username"].apply(_anonymous_user_id)

    score_columns = [
        "conversation_flow",
        "profile_reality_match",
        "comfort_safety",
        "spark",
    ]

    for col in score_columns:
        df[col] = df[col].apply(_to_number)

    df["second_date_bool"] = df["second_date"].apply(_yes_no_to_bool)

    return df


def _build_profile_tokens(row: pd.Series) -> List[str]:
    """
    אלו הפיצ'רים שמייצגים את מה שהופיע בפרופיל לפני הדייט.
    הם ישמשו את predictor / correlations.
    """
    tokens = []

    app = _normalize_text(row.get("dating_app"))
    career = _normalize_text(row.get("profile_career"))
    visual_vibe = _normalize_text(row.get("profile_visual_vibe"))

    if app:
        tokens.append(f"app:{app}")

    if career:
        tokens.append(f"profile:{career}")

    if visual_vibe:
        tokens.append(f"vibe:{visual_vibe}")

    for interest in _split_tags(row.get("profile_interests")):
        tokens.append(f"interest:{interest}")

    return tokens


def _build_vas_scores(row: pd.Series) -> Dict[str, float]:
    """
    VAS scores = הציונים הסובייקטיביים מחוויית הדייט.
    נשמור אותם גם בנפרד, וגם נחשב מהם ציון מרכזי.
    """
    return {
        "conversation_flow": float(row["conversation_flow"]),
        "profile_reality_match": float(row["profile_reality_match"]),
        "comfort_safety": float(row["comfort_safety"]),
        "spark": float(row["spark"]),
    }


def _primary_vas(vas_scores: Dict[str, float]) -> float:
    """
    ציון חוויית דייט כללי.
    כרגע ממוצע פשוט של ארבעת המדדים.
    אפשר בהמשך לשנות משקלים.
    """
    values = list(vas_scores.values())
    return sum(values) / len(values) if values else 0.0


def dataframe_to_date_records(df: pd.DataFrame) -> List[DateRecord]:
    records: List[DateRecord] = []

    for _, row in df.iterrows():
        vas_scores = _build_vas_scores(row)
        profile_tokens = _build_profile_tokens(row)

        topic_tags = _split_tags(row.get("conversation_topics"))
        vibe_tags = _split_tags(row.get("date_dynamic_tags"))

        record = DateRecord(
            user_id=row["user_id"],
            vas=_primary_vas(vas_scores),
            vas_scores=vas_scores,
            profile=profile_tokens,
            tags=vibe_tags,
            topic_tags=topic_tags,
            vibe_tags=vibe_tags,
            sentiment=0.0,
            second_date=row["second_date_bool"],
            raw_text=_normalize_text(row.get("free_text")),
        )

        records.append(record)

    return records


def load_questionnaire_history() -> Tuple[List[DateRecord], pd.DataFrame, pd.DataFrame]:
    """
    הפונקציה המרכזית:
    מחזירה history שהמערכת הקיימת כבר יודעת לעבוד איתו,
    בנוסף לטבלאות המקוריות למקרה שנרצה תובנות נוספות.
    """
    baseline_df = load_baseline_dataframe()
    date_df = load_date_experience_dataframe()
    history = dataframe_to_date_records(date_df)

    return history, baseline_df, date_df