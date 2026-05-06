import logging
import secrets
from datetime import datetime

from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from togai.throttles import ScanThrottle

from catalog.models import Species
from togai.integrations import identify_species_from_image

from .models import Observation
from .serializers import ObservationSerializer, ScanRequestSerializer

log = logging.getLogger(__name__)


class ObservationViewSet(viewsets.ModelViewSet):
    serializer_class = ObservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    queryset = Observation.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Observation.objects.none()
        return Observation.objects.filter(user=self.request.user).select_related("species")

    @action(
        detail=False,
        methods=["get"],
        url_path="yearbook",
        permission_classes=[permissions.IsAuthenticated],
    )
    def yearbook(self, request):
        """Yillik PDF kitob — joriy foydalanuvchining barcha skanlari.

        GET ?year=2026 (default = current year)
        Returns: application/pdf
        """
        from django.http import HttpResponse
        from .yearbook import render_yearbook
        try:
            year = int(request.query_params.get("year") or datetime.now().year)
        except ValueError:
            year = datetime.now().year
        from datetime import datetime as _dt
        start = _dt(year, 1, 1)
        end = _dt(year + 1, 1, 1)
        obs = (
            Observation.objects.filter(
                user=request.user,
                created_at__gte=start, created_at__lt=end,
            )
            .select_related("species")
            .order_by("created_at")
        )
        pdf = render_yearbook(request.user, year, obs)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = (
            f'attachment; filename="togai-kundalik-{year}.pdf"'
        )
        return resp

    @action(
        detail=False,
        methods=["get"],
        url_path="public",
        permission_classes=[permissions.AllowAny],
    )
    def public(self, request):
        """Global feed — barcha foydalanuvchilarning GPS-li skanlari.

        GET ?bbox=minLat,minLng,maxLat,maxLng (optional) → bounding box filter
        GET ?limit=200 (default 200, max 500)
        """
        from django.db.models import Q
        qs = (
            Observation.objects
            .filter(latitude__isnull=False, longitude__isnull=False)
            .select_related("species", "user")
            .order_by("-created_at")
        )
        bbox = request.query_params.get("bbox")
        if bbox:
            try:
                a, b, c, d = [float(x) for x in bbox.split(",")[:4]]
                qs = qs.filter(
                    latitude__gte=min(a, c), latitude__lte=max(a, c),
                    longitude__gte=min(b, d), longitude__lte=max(b, d),
                )
            except (TypeError, ValueError):
                pass
        try:
            limit = max(1, min(500, int(request.query_params.get("limit") or 200)))
        except ValueError:
            limit = 200
        qs = qs[:limit]
        ser = ObservationSerializer(qs, many=True, context={"request": request})
        return Response({"count": len(ser.data), "results": ser.data})

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=False,
        methods=["post"],
        url_path="scan",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[permissions.AllowAny],
        throttle_classes=[ScanThrottle],
    )
    def scan(self, request):
        """AI tur aniqlash — Groq Vision (llama-3.2-90b-vision).

        POST multipart: photo, lat?, lng?
        Response: {identified: bool, species: {...}, confidence: float, meta: {...}}
        """
        req = ScanRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)

        photo = req.validated_data["photo"]
        image_bytes = photo.read()
        photo.seek(0)

        # 1. Groq Vision bilan aniqlash
        result = identify_species_from_image(image_bytes, mime=photo.content_type or "image/jpeg")

        if not result.get("found"):
            # AI ishonchsiz — TUR YO'Q, foydalanuvchiga rost gap aytamiz (random fallback EMAS)
            return Response(
                {
                    "identified": False,
                    "reason": result.get("reason") or "Rasmda biologik tur topilmadi",
                },
                status=status.HTTP_200_OK,
            )

        # 2. Groq javobi — Species'ni yangilash yoki yaratish
        latin = (result.get("latin") or "").strip()
        name = (result.get("name") or "").strip() or latin

        # OVERRIDE: if AI's latin maps to our UZ vocab, use the authoritative UZ name
        from search.uz_vocab import resolve_latin
        uz_lookup = resolve_latin(latin)
        if uz_lookup:
            name = uz_lookup["uz"]
            # also use canonical latin from vocab (more accurate than AI)
            if not latin or latin.lower() != uz_lookup["latin"].lower():
                latin = uz_lookup["latin"]
        else:
            # Vocab'da yo'q — AI tarjimon bilan ingliz nomni o'zbekchaga
            try:
                from togai.services.translate import translate_one
                tr = translate_one(name, latin)
                if tr and tr != name:
                    name = tr
            except Exception:
                pass

        slug = slugify(latin or name) or f"tur-{secrets.token_hex(4)}"

        # Universal UZ: hamma matn maydonlarini tekshir
        summary = (result.get("summary") or "")[:280]
        description = result.get("description") or ""
        habitat = result.get("habitat") or ""
        uses = result.get("uses") or ""
        warnings = result.get("warnings") or ""
        first_aid = result.get("first_aid") or ""
        regions = result.get("regions") or ""
        try:
            from togai.services.translate import ensure_uz
            if summary: summary = ensure_uz(summary, kind="auto")
            if description: description = ensure_uz(description, kind="block")
            if habitat: habitat = ensure_uz(habitat, kind="auto")
            if uses: uses = ensure_uz(uses, kind="auto")
            if warnings: warnings = ensure_uz(warnings, kind="auto")
            if first_aid: first_aid = ensure_uz(first_aid, kind="auto")
            if regions: regions = ensure_uz(regions, kind="auto")
        except Exception:
            pass

        species, created = Species.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name or latin,
                "latin": latin,
                "category": result.get("category") or "giyoh",
                "icon_name": {
                    "giyoh": "leaf", "daraxt": "tree", "gul": "flower",
                    "jonivor": "paw", "hasharot": "paw", "qush": "paw",
                }.get(result.get("category"), "leaf"),
                "summary": summary,
                "description": description,
                "habitat": habitat,
                "uses": uses,
                "warnings": warnings,
                "first_aid": first_aid,
                "red_book": bool(result.get("red_book")),
                "iucn_status": (result.get("iucn_status") or "NE")[:4],
                "regions": regions,
            },
        )

        # 3. Kuzatuv yaratish + Avtomatik kolleksiyaga qo'shish
        confidence = float(result.get("confidence") or 0.9)
        obs = None
        if request.user.is_authenticated:
            obs = Observation.objects.create(
                user=request.user,
                species=species,
                photo=photo,
                ai_confidence=confidence,
                latitude=req.validated_data.get("latitude"),
                longitude=req.validated_data.get("longitude"),
            )
            # Auto-save to user portfolio (kolleksiya). Birinchi marta yaratiladi,
            # ikkinchi marta — get_or_create idempotent
            try:
                from saved_items.models import SavedSpecies
                SavedSpecies.objects.get_or_create(
                    user=request.user,
                    species=species,
                    defaults={"note": ""},
                )
            except Exception:
                # Kolleksiya yaratish xato bo'lsa — scan asosiy ish, davom etamiz
                logging.getLogger(__name__).exception("auto-save to portfolio failed")

        return Response({
            "identified": True,
            "fallback": False,
            "species": {
                "slug": species.slug,
                "name": species.name,
                "latin": species.latin,
                "category": species.category,
                "summary": species.summary,
                "description": species.description,
                "habitat": species.habitat,
                "uses": species.uses,
                "warnings": species.warnings,
                "first_aid": species.first_aid,
                "red_book": species.red_book,
                "iucn_status": species.iucn_status,
                "regions": species.regions,
                "similar_species": result.get("similar_species") or [],
                "alternatives": [
                    {
                        **a,
                        # Override alt name from vocab if Latin matches
                        "name": (resolve_latin(a.get("latin", "")) or {}).get("uz") or a.get("name"),
                    }
                    for a in (result.get("alternatives") or [])
                    if isinstance(a, dict)
                ],
                "key_features": result.get("key_features") or "",
                "picture": request.build_absolute_uri(obs.photo.url) if obs and obs.photo else None,
            },
            "confidence": confidence,
            "observation_id": obs.id if obs else None,
            "new_species": created,
        })
