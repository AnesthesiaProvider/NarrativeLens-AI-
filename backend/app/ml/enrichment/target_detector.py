"""Layer 2: Protected demographic group detector.

Uses curated lexicons and regex patterns to identify which protected
identity group is being targeted in a piece of hate speech text.
Covers English and common Hinglish/Hindi transliterations.

Returns a TargetGroupResult with label, optional detail, and confidence.
Confidence is derived from signal density (count & weight), not model probability.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Identity Signal Lexicons
# Each entry: (pattern_string, weight, detail_label)
# Weight 1.0 = strong identity signal, 0.5 = moderate, 0.3 = weak/contextual
# ---------------------------------------------------------------------------

_RELIGION_SIGNALS: List[Tuple[str, float, str]] = [
    # Islam
    (r"\bmuslim[s]?\b", 1.0, "Muslim"),
    (r"\bislam[ic]?\b", 0.9, "Muslim"),
    (r"\bmosque[s]?\b", 0.8, "Muslim"),
    (r"\bmuslim[s]?\b", 1.0, "Muslim"),
    (r"\bjihad[i]?\b", 0.9, "Muslim"),
    (r"\bkafir[s]?\b", 1.0, "Muslim"),
    (r"\bmullah[s]?\b", 0.8, "Muslim"),
    (r"\bterrorist[s]?\b.*\bislam", 1.0, "Muslim"),
    # Judaism
    (r"\bjew[s]?\b", 1.0, "Jewish"),
    (r"\bjewish\b", 1.0, "Jewish"),
    (r"\bsynagogue[s]?\b", 0.8, "Jewish"),
    (r"\bzionist[s]?\b", 0.9, "Jewish"),
    (r"\bhebrew[s]?\b", 0.7, "Jewish"),
    (r"\banti.?semiti[c|sm]\b", 1.0, "Jewish"),
    # Christianity
    (r"\bchristian[s]?\b", 1.0, "Christian"),
    (r"\bchurch[es]?\b", 0.8, "Christian"),
    (r"\bcrusader[s]?\b", 0.9, "Christian"),
    (r"\binfidel[s]?\b", 0.9, "Christian"),
    # Hinduism
    (r"\bhindu[s]?\b", 1.0, "Hindu"),
    (r"\bhinduism\b", 1.0, "Hindu"),
    (r"\btemple[s]?\b", 0.5, "Hindu"),
    (r"\bmandir[s]?\b", 0.8, "Hindu"),
    (r"\bkafir[s]?\b", 0.8, "Hindu"),
    # Generic religion
    (r"\breligion[s]?\b", 0.4, None),
    (r"\bfaith\b", 0.3, None),
    (r"\bgod[s]?\b", 0.3, None),
    # Hinglish transliterations
    (r"\bmullo\b", 1.0, "Muslim"),
    (r"\bkatiyo\b", 0.9, "Hindu"),
    (r"\bmulla[h]?\b", 0.8, "Muslim"),
]

_RACE_ETHNICITY_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bblack[s]?\b", 0.7, "Black/African"),
    (r"\bwhite[s]?\b", 0.6, None),
    (r"\bafrican[s]?\b", 0.7, "Black/African"),
    (r"\basia[n]?\b", 0.6, "Asian"),
    (r"\bchines[e]?\b", 0.8, "Chinese"),
    (r"\bindian[s]?\b", 0.7, "Indian"),
    (r"\bpakistani[s]?\b", 0.8, "Pakistani"),
    (r"\barab[s]?\b", 0.8, "Arab"),
    (r"\bhispanic[s]?\b", 0.8, "Hispanic"),
    (r"\blatino[s|a]?\b", 0.8, "Latino"),
    (r"\bmonkey[s]?\b", 0.9, None),  # racial dehumanization
    (r"\bape[s]?\b", 0.9, None),     # racial dehumanization
    (r"\bsubhuman[s]?\b", 1.0, None),
    (r"\bthose people\b", 0.5, None),
    (r"\bthat race\b", 0.6, None),
    (r"\bethni[c|city]\b", 0.5, None),
    (r"\brace[s]?\b", 0.4, None),
    (r"\bangrezo\b", 0.7, "White/British"),  # Hinglish
    (r"\bchino\b", 0.7, "Chinese"),
]

_GENDER_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bwomen?\b", 0.7, "Women"),
    (r"\bfemale[s]?\b", 0.7, "Women"),
    (r"\bgirls?\b", 0.6, "Women"),
    (r"\bfeminist[s]?\b", 0.8, "Women"),
    (r"\bwitch[es]?\b", 0.6, "Women"),
    (r"\bslut[s]?\b", 1.0, "Women"),
    (r"\bwhor[e|es]\b", 1.0, "Women"),
    (r"\bcunt[s]?\b", 1.0, "Women"),
    (r"\btrann[y|ies]\b", 1.0, "Transgender"),
    (r"\btransgender[s]?\b", 0.9, "Transgender"),
    (r"\btrans\b", 0.7, "Transgender"),
    (r"\bmen\b", 0.4, "Men"),
    (r"\bmale[s]?\b", 0.4, "Men"),
    (r"\bauratein?\b", 0.8, "Women"),  # Hinglish: "women"
    (r"\blarki[ya]?\b", 0.7, "Women"),  # Hinglish: "girl"
]

_SEXUAL_ORIENTATION_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bgay[s]?\b", 0.9, "Gay"),
    (r"\blesbians?\b", 0.9, "Lesbian"),
    (r"\bhomosexual[s]?\b", 0.9, "LGBTQ+"),
    (r"\bqueer[s]?\b", 0.8, "LGBTQ+"),
    (r"\blgbt[qi+]?\b", 0.9, "LGBTQ+"),
    (r"\bfag[s|got]?\b", 1.0, "Gay"),
    (r"\bdyke[s]?\b", 1.0, "Lesbian"),
    (r"\bsodomite[s]?\b", 1.0, "LGBTQ+"),
    (r"\bsexual orientation\b", 0.5, "LGBTQ+"),
]

_NATIONALITY_IMMIGRATION_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bimmigrant[s]?\b", 1.0, "Immigrants"),
    (r"\billegal[s]?\b", 0.9, "Immigrants"),
    (r"\bforeigner[s]?\b", 0.9, "Foreigners"),
    (r"\brefugee[s]?\b", 0.8, "Refugees"),
    (r"\bsend them back\b", 1.0, "Immigrants"),
    (r"\binvasion\b", 0.9, "Immigrants"),
    (r"\bopen border[s]?\b", 0.7, "Immigrants"),
    (r"\bghuspaithiye\b", 1.0, "Immigrants"),  # Hinglish: "infiltrators"
    (r"\bvidehi[ya]?\b", 0.8, "Foreigners"),   # Hinglish
    (r"\bdeport[ed|ation]?\b", 0.9, "Immigrants"),
    (r"\bborder\b", 0.4, None),
    (r"\bnational[s]?\b", 0.3, None),
]

_DISABILITY_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bret[a|e]rd[ed|s]?\b", 1.0, "Cognitive Disability"),
    (r"\bcrip[ple|pled|s]?\b", 1.0, "Physical Disability"),
    (r"\bautistic\b", 0.8, "Autism"),
    (r"\bmentally ill\b", 0.8, "Mental Illness"),
    (r"\bdisabled\b", 0.6, "Disability"),
    (r"\bhandicapped\b", 0.7, "Disability"),
    (r"\bgenetic burden\b", 1.0, "Disability"),
    (r"\bfreak[s]?\b", 0.5, None),
]

_POLITICAL_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bcommun[ist|ism]\b", 0.8, "Communist"),
    (r"\bnazi[s]?\b", 1.0, "Nazi"),
    (r"\bfascis[t|m]\b", 0.9, "Fascist"),
    (r"\bleftist[s]?\b", 0.7, "Left-Wing"),
    (r"\blibtard[s]?\b", 0.9, "Left-Wing"),
    (r"\bconservative[s]?\b", 0.5, "Right-Wing"),
    (r"\bmaga\b", 0.6, "MAGA"),
    (r"\bwoke\b", 0.5, None),
    (r"\bsocialist[s]?\b", 0.6, "Socialist"),
]

_SOCIOECONOMIC_SIGNALS: List[Tuple[str, float, str]] = [
    (r"\bpoor\b", 0.5, "Poor"),
    (r"\bwelfare\b", 0.6, "Welfare Recipients"),
    (r"\bbum[s]?\b", 0.7, "Homeless"),
    (r"\bhomeless\b", 0.6, "Homeless"),
    (r"\bunderclass\b", 0.8, "Lower Class"),
    (r"\bparasite[s]?\b", 0.8, None),
    (r"\bleech[es]?\b", 0.7, None),
]

# Compile all signal sets into pattern groups
_SIGNAL_GROUPS: Dict[str, List[Tuple[str, float, str]]] = {
    "Religion": _RELIGION_SIGNALS,
    "Race/Ethnicity": _RACE_ETHNICITY_SIGNALS,
    "Gender": _GENDER_SIGNALS,
    "Sexual Orientation": _SEXUAL_ORIENTATION_SIGNALS,
    "Nationality/Immigration": _NATIONALITY_IMMIGRATION_SIGNALS,
    "Disability": _DISABILITY_SIGNALS,
    "Political/Ideological": _POLITICAL_SIGNALS,
    "Socioeconomic": _SOCIOECONOMIC_SIGNALS,
}

# Pre-compile regex patterns once at module load for performance
_COMPILED_GROUPS: Dict[str, List[Tuple[re.Pattern, float, Optional[str]]]] = {}
for _group, _signals in _SIGNAL_GROUPS.items():
    _COMPILED_GROUPS[_group] = [
        (re.compile(pat, re.IGNORECASE | re.UNICODE), weight, detail)
        for pat, weight, detail in _signals
    ]


class TargetGroupDetector:
    """Detects which protected demographic group is targeted in text.

    Uses curated lexicon signal matching across 8 protected categories.
    Returns the strongest match with a signal-density confidence score.
    """

    # Minimum cumulative signal weight to report a category
    _MIN_CONFIDENCE_THRESHOLD = 0.35

    def detect(self, text: str) -> Dict:
        """Run target group detection on the given text.

        Returns a dict compatible with TargetGroupResult schema:
          { label, detail, confidence }
        """
        if not text or not text.strip():
            return {"label": "None", "detail": None, "confidence": 0.0}

        text_lower = text.lower()
        group_scores: Dict[str, float] = {}
        group_details: Dict[str, Optional[str]] = {}

        for group_name, compiled_patterns in _COMPILED_GROUPS.items():
            cumulative_weight = 0.0
            best_detail: Optional[str] = None
            best_detail_weight = 0.0

            for pattern, weight, detail in compiled_patterns:
                matches = pattern.findall(text_lower)
                if matches:
                    # Diminishing returns for repeated signals of same type
                    match_boost = weight * (1.0 + 0.2 * (len(matches) - 1))
                    cumulative_weight += min(match_boost, weight * 2.0)
                    if detail and weight > best_detail_weight:
                        best_detail = detail
                        best_detail_weight = weight

            if cumulative_weight > 0:
                group_scores[group_name] = round(min(cumulative_weight, 1.0), 4)
                group_details[group_name] = best_detail

        if not group_scores:
            return {"label": "None", "detail": None, "confidence": 0.0}

        # Check for intersectional targeting (2+ groups both above threshold)
        active_groups = [
            g for g, s in group_scores.items()
            if s >= self._MIN_CONFIDENCE_THRESHOLD
        ]
        if len(active_groups) >= 2:
            top_group = max(group_scores, key=lambda g: group_scores[g])
            return {
                "label": "Multiple/Intersectional",
                "detail": f"{active_groups[0]} + {active_groups[1]}",
                "confidence": round(max(group_scores.values()), 4),
            }

        # Single strongest group
        top_group = max(group_scores, key=lambda g: group_scores[g])
        top_score = group_scores[top_group]

        if top_score < self._MIN_CONFIDENCE_THRESHOLD:
            return {"label": "None", "detail": None, "confidence": round(top_score, 4)}

        return {
            "label": top_group,
            "detail": group_details.get(top_group),
            "confidence": round(top_score, 4),
        }
