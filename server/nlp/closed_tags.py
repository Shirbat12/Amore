"""The closed list of ~15-20 character / communication-style tags (section 2.3.1).

A *closed* list (rather than free tagging) is what makes tags comparable across
dates and therefore correlate-able downstream. Each tag is grounded in the
personality/attraction literature (Big Five; Interpersonal Circumplex - Wiggins
1979; Fletcher et al. 1999; Reis & Gable 2015; Wilbur & Campbell 2011).

CLOSED_TAGS holds the Hebrew labels the model must choose from. TAG_KEYWORDS maps
each tag to surface words used by the offline mock tagger (no API key needed).
TAG_VALENCE marks positive (+1) vs negative (-1) tags for sentiment fallback.
"""
from __future__ import annotations

# Hebrew label -> English slug (slug used by data/tag_taxonomy.csv and tests).
TAG_SLUGS = {
    "חמים": "warm",
    "אכפתי": "caring",
    "אותנטי": "authentic",
    "נעים": "pleasant",
    "מקשיב": "listener",
    "מתעניין": "interested",
    "זורם בשיחה": "conversational",
    "דברן": "talkative",
    "אנרגטי": "energetic",
    "בטוח בעצמו": "confident",
    "מצחיק": "funny",
    "שנון": "witty",
    "קליל": "lighthearted",
    "מושך": "attractive",
    "תוסס": "lively",
    "מרוחק": "distant",
    "מתנשא": "arrogant",
    "מרוכז בעצמו": "self_centered",
    "משעמם": "boring",
}

CLOSED_TAGS = list(TAG_SLUGS.keys())

# Negative-valence tags (the rest are positive). Used by the mock sentiment.
_NEGATIVE = {"מרוחק", "מתנשא", "מרוכז בעצמו", "משעמם"}
TAG_VALENCE = {t: (-1 if t in _NEGATIVE else 1) for t in CLOSED_TAGS}

# Surface keywords for the offline mock tagger. Maps a tag to words/roots whose
# presence in the free text implies the tag. Intentionally lightweight.
TAG_KEYWORDS = {
    "חמים": ["חמים", "חום", "לבבי"],
    "אכפתי": ["אכפת", "דאג", "התחשב"],
    "אותנטי": ["אותנטי", "כן", "אמיתי", "טבעי"],
    "נעים": ["נעים", "נחמד", "כיף"],
    "מקשיב": ["הקשיב", "מקשיב", "הקשבה"],
    "מתעניין": ["התעניין", "שאל", "סקרן"],
    "זורם בשיחה": ["זרמה", "זורם", "זרימה", "שיחה זרמה"],
    "דברן": ["דברן", "דיבר הרבה", "פטפט"],
    "אנרגטי": ["אנרגטי", "אנרגיה", "מלא חיים"],
    "בטוח בעצמו": ["בטוח בעצמו", "ביטחון"],
    "מצחיק": ["מצחיק", "צחקנו", "הומור", "צחוק"],
    "שנון": ["שנון", "חד", "ציני בקטע טוב"],
    "קליל": ["קליל", "קלילה", "רגוע"],
    "מושך": ["מושך", "משיכה", "חתיך", "סקסי"],
    "תוסס": ["תוסס", "שמח", "ססגוני"],
    "מרוחק": ["מרוחק", "קר", "מנותק"],
    "מתנשא": ["מתנשא", "יהיר", "התנשא"],
    "מרוכז בעצמו": ["מרוכז בעצמו", "דיבר רק על עצמו", "אגו"],
    "משעמם": ["משעמם", "שעמום", "תקוע", "מאולץ"],
}
