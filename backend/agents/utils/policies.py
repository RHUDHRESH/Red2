from __future__ import annotations

from typing import Dict


# Platform/content length policies (best-effort industry norms)
EMAIL = {
    "subject_max": 60,
    "preheader_max": 90,
}

PUSH = {
    "title_max": 40,
    "body_max": 80,
    "cta_max": 30,
}

SMS = {
    "variant_max": 160,
}

HEADLINE_MAX = 70
HOOK_MAX = 80
CTA_MAX = 24
TAGLINE_MAX = 30

