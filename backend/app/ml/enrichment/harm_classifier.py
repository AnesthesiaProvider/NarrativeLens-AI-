"""Layer 3: Harm type classifier.

Classifies the specific *type* of harm present in text, independent of
which demographic group is targeted. Uses curated signal lexicons and
contextual pattern matching.

Six harm categories (priority-ordered):
  1. Incitement to Violence  — calls to attack, kill, remove by force
  2. Dehumanization          — animal/pest/disease metaphors
  3. Slur                    — recognized identity-based slurs
  4. Harassment/Intimidation — targeted personal threats
  5. Stereotype Reinforcement — group-level negative generalisations
  6. Profanity/Aggression    — strong offensive language without group targeting
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Harm Signal Lexicons
# Each entry: (pattern_string, weight)
# ---------------------------------------------------------------------------

_INCITEMENT_SIGNALS: List[Tuple[str, float]] = [
    (r"\bkill\b", 1.0),
    (r"\bkill them\b", 1.0),
    (r"\bmurder\b", 1.0),
    (r"\bshoot\b", 0.9),
    (r"\battack\b", 0.8),
    (r"\bexterminate\b", 1.0),
    (r"\bwipe out\b", 1.0),
    (r"\bwipe them out\b", 1.0),
    (r"\beliminate\b", 0.9),
    (r"\bdestroy\b", 0.7),
    (r"\bslaughter\b", 1.0),
    (r"\bpurge\b", 1.0),
    (r"\bcleanse\b", 0.9),
    (r"\bremove them\b", 0.8),
    (r"\bdeport\b", 0.7),
    (r"\bburn\b.*\bdown\b", 0.9),
    (r"\bjaan se maar\b", 1.0),   # Hinglish: "kill them"
    (r"\bgoli maar\b", 1.0),      # Hinglish: "shoot"
    (r"\bkhatam kar\b", 1.0),     # Hinglish: "finish off / destroy"
    (r"\bmaar do\b", 1.0),        # Hinglish: "kill"
    (r"\bjalaa do\b", 1.0),       # Hinglish: "burn them"
    (r"\bdeath to\b", 1.0),
    (r"\bexecute\b", 0.9),
    (r"\bshoot on sight\b", 1.0),
    (r"\bpogrom\b", 1.0),
    (r"\bgenocide\b", 1.0),
    (r"\bhang them\b", 1.0),
]

_DEHUMANIZATION_SIGNALS: List[Tuple[str, float]] = [
    (r"\bvermin\b", 1.0),
    (r"\bcockroach(es)?\b", 1.0),
    (r"\bparasite[s]?\b", 1.0),
    (r"\bpest[s]?\b", 0.8),
    (r"\bmonkey[s]?\b", 0.9),
    (r"\bape[s]?\b", 0.9),
    (r"\brat[s]?\b", 0.7),
    (r"\bsubhuman[s]?\b", 1.0),
    (r"\bsavage[s]?\b", 0.9),
    (r"\banimals?\b", 0.6),
    (r"\bbeast[s]?\b", 0.7),
    (r"\bscum\b", 0.8),
    (r"\bfilth\b", 0.8),
    (r"\binfestati[on|ng]\b", 1.0),
    (r"\bpollut(e|ing|ion)\b", 0.6),
    (r"\bdisease\b.*\bspread\b", 0.8),
    (r"\bsuar\b", 1.0),           # Hinglish: "pig" (derogatory)
    (r"\bkeede?\b", 0.9),         # Hinglish: "insects"
    (r"\bkamino\b", 0.9),         # Hinglish: "scum"
    (r"\binfestation\b", 1.0),
    (r"\bthey.*like.*animal\b", 0.9),
]

_SLUR_SIGNALS: List[Tuple[str, float]] = [
    # These are sanitized pattern references — the actual patterns detect
    # the slur shapes without reproducing them verbatim in clean source code.
    # Common racial/ethnic slurs (derogatory phoneme patterns)
    (r"\bn[i1!][g6][g6][ae3][r]?\b", 1.0),
    (r"\bsp[i1!][c]k?\b", 1.0),
    (r"\bch[i1!]nk[s]?\b", 1.0),
    (r"\bwet.?back[s]?\b", 1.0),
    (r"\bk[i1!]ke[s]?\b", 1.0),
    (r"\bcoon[s]?\b", 1.0),
    (r"\bgook[s]?\b", 1.0),
    (r"\bwop[s]?\b", 0.9),
    # Gender / sexuality slurs
    (r"\bfagg?[oi]t[s]?\b", 1.0),
    (r"\bdyk(e|es)\b", 1.0),
    (r"\btrann[y|ies]\b", 1.0),
    (r"\bshemale[s]?\b", 1.0),
    (r"\bslut[s]?\b", 1.0),
    (r"\bwhor(e|es)\b", 1.0),
    (r"\bcunt[s]?\b", 1.0),
    # Disability slurs
    (r"\bret[a|e]rd(ed|s)?\b", 1.0),
    (r"\bcrip(ple|pled)?\b", 0.9),
    # Hinglish slurs (transliterated)
    (r"\bmullo\b", 1.0),
    (r"\bkatiyo\b", 1.0),
    (r"\blandiya\b", 1.0),
    (r"\bmadarchod\b", 1.0),
    (r"\bbenchod\b", 0.9),
    (r"\bchutiye\b", 0.9),
]

_HARASSMENT_SIGNALS: List[Tuple[str, float]] = [
    (r"\byou will regret\b", 1.0),
    (r"\bi know where you (live|are)\b", 1.0),
    (r"\bwe will find you\b", 1.0),
    (r"\bwatch your back\b", 0.9),
    (r"\bcome after you\b", 0.9),
    (r"\bshut (your|the) (mouth|face|up)\b", 0.7),
    (r"\bdoxx(ing|ed)?\b", 1.0),
    (r"\bstalk(ing|ed)?\b", 0.8),
    (r"\bthreaten(ed|ing)?\b", 0.8),
    (r"\breported\b.*\bsuspended\b", 0.6),
    (r"\bget out\b", 0.5),
    (r"\bterroriz(e|ing)\b", 0.9),
]

_STEREOTYPE_SIGNALS: List[Tuple[str, float]] = [
    (r"\bthey all\b", 0.7),
    (r"\bthose people always\b", 0.8),
    (r"\ball (of )?them\b", 0.6),
    (r"\balways (criminal|violent|lazy|corrupt)\b", 0.8),
    (r"\bborn to\b.*\b(steal|cheat|lie|kill)\b", 0.9),
    (r"\btheir kind\b", 0.8),
    (r"\btheir nature\b", 0.7),
    (r"\bin their (dna|blood|genes)\b", 0.9),
    (r"\bsabhi.*hain\b", 0.6),   # Hinglish: "all of them are..."
    (r"\bgenetically\b.*\b(inferior|superior)\b", 0.9),
]

_PROFANITY_AGGRESSION_SIGNALS: List[Tuple[str, float]] = [
    (r"\bfuck\b", 0.5),
    (r"\bshit\b", 0.4),
    (r"\bassh[o0]le[s]?\b", 0.6),
    (r"\bstupid\b", 0.3),
    (r"\bidiot[s]?\b", 0.4),
    (r"\bmoron[s]?\b", 0.5),
    (r"\bimbecilic?\b", 0.5),
    (r"\bgo to hell\b", 0.6),
    (r"\bdamn\b", 0.3),
    (r"\bcrap\b", 0.3),
    (r"\bbastard[s]?\b", 0.6),
    (r"\bpiss off\b", 0.6),
    (r"\bkutte\b", 0.5),         # Hinglish: "dog" (generic insult)
    (r"\bbewakoof\b", 0.4),      # Hinglish: "fool"
    (r"\bnikamma\b", 0.4),       # Hinglish: "useless"
]

# ---------------------------------------------------------------------------
# Compile patterns once at module load
# ---------------------------------------------------------------------------

_COMPILED_HARM: Dict[str, List[Tuple[re.Pattern, float]]] = {
    "Incitement to Violence": [
        (re.compile(p, re.IGNORECASE | re.UNICODE), w)
        for p, w in _INCITEMENT_SIGNALS
    ],
    "Dehumanization": [
        (re.compile(p, re.IGNORECASE | re.UNICODE), w)
        for p, w in _DEHUMANIZATION_SIGNALS
    ],
    "Slur": [
        (re.compile(p, re.IGNORECASE | re.UNICODE), w)
        for p, w in _SLUR_SIGNALS
    ],
    "Harassment/Intimidation": [
        (re.compile(p, re.IGNORECASE | re.UNICODE), w)
        for p, w in _HARASSMENT_SIGNALS
    ],
    "Stereotype Reinforcement": [
        (re.compile(p, re.IGNORECASE | re.UNICODE), w)
        for p, w in _STEREOTYPE_SIGNALS
    ],
    "Profanity/Aggression": [
        (re.compile(p, re.IGNORECASE | re.UNICODE), w)
        for p, w in _PROFANITY_AGGRESSION_SIGNALS
    ],
}

# Priority order: higher-severity harm types take precedence when tied
_HARM_PRIORITY = [
    "Incitement to Violence",
    "Slur",
    "Dehumanization",
    "Harassment/Intimidation",
    "Stereotype Reinforcement",
    "Profanity/Aggression",
]


class HarmClassifier:
    """Classifies the type of harm present in text.

    Uses ordered priority: incitement > slur > dehumanization >
    harassment > stereotype > profanity.
    Returns a dict compatible with HarmTypeResult schema.
    """

    _MIN_SIGNAL_THRESHOLD = 0.3

    def classify(self, text: str) -> Dict:
        """Classify harm type from text.

        Returns:
            dict with keys: label, confidence
        """
        if not text or not text.strip():
            return {"label": "None", "confidence": 0.0}

        harm_scores: Dict[str, float] = {}

        for harm_name, compiled_patterns in _COMPILED_HARM.items():
            cumulative = 0.0
            for pattern, weight in compiled_patterns:
                matches = pattern.findall(text)
                if matches:
                    cumulative += weight * min(len(matches), 3)  # cap at 3 hits per pattern
            if cumulative > 0:
                harm_scores[harm_name] = round(min(cumulative, 1.0), 4)

        if not harm_scores:
            return {"label": "None", "confidence": 0.0}

        # Apply priority ordering: pick highest-priority harm type that
        # meets the threshold, not necessarily the highest raw score.
        for harm_type in _HARM_PRIORITY:
            score = harm_scores.get(harm_type, 0.0)
            if score >= self._MIN_SIGNAL_THRESHOLD:
                return {"label": harm_type, "confidence": score}

        # No harm type met the threshold
        best = max(harm_scores, key=lambda h: harm_scores[h])
        return {"label": best, "confidence": harm_scores[best]}
