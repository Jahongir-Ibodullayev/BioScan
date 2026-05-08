"""Fast JSON renderer using orjson (3-5x faster than stdlib json).

Falls back to DRF's default renderer if orjson is missing.
"""
from __future__ import annotations

try:
    import orjson  # type: ignore
except ImportError:  # pragma: no cover
    orjson = None

from rest_framework.renderers import JSONRenderer


class OrjsonRenderer(JSONRenderer):
    media_type = "application/json"
    format = "json"
    charset = None  # orjson always returns UTF-8 bytes

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if orjson is None:
            return super().render(data, accepted_media_type, renderer_context)
        # OPT_NON_STR_KEYS — be permissive (DRF sometimes passes int keys)
        # OPT_SERIALIZE_NUMPY — harmless when numpy isn't loaded
        return orjson.dumps(
            data,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
            default=str,
        )
