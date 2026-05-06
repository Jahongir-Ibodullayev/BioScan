"""Custom throttle classes — har biri belgilangan rate scope ishlatadi.

Settings.py'dagi DEFAULT_THROTTLE_RATES bilan bog'lanadi:
  scan, ai_chat, ai_enrich, ai_help
"""
from rest_framework.throttling import ScopedRateThrottle


class ScanThrottle(ScopedRateThrottle):
    scope = "scan"


class AIChatThrottle(ScopedRateThrottle):
    scope = "ai_chat"


class AIEnrichThrottle(ScopedRateThrottle):
    scope = "ai_enrich"


class AIHelpThrottle(ScopedRateThrottle):
    scope = "ai_help"
