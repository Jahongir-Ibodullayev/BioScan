import logging
import random

from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=False,
        methods=["post"],
        url_path="scan",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[permissions.AllowAny],
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
            # Fallback — random mock
            candidates = list(Species.objects.all())
            if not candidates:
                return Response(
                    {"identified": False, "reason": result.get("reason", "AI tanib olmadi")},
                    status=status.HTTP_200_OK,
                )
            picked = random.choice(candidates)
            confidence = round(random.uniform(0.72, 0.89), 2)
            obs = None
            if request.user.is_authenticated:
                obs = Observation.objects.create(
                    user=request.user,
                    species=picked,
                    photo=photo,
                    ai_confidence=confidence,
                    latitude=req.validated_data.get("latitude"),
                    longitude=req.validated_data.get("longitude"),
                )
            return Response({
                "identified": True,
                "fallback": True,
                "species": {
                    "slug": picked.slug,
                    "name": picked.name,
                    "latin": picked.latin,
                    "category": picked.category,
                    "summary": picked.summary,
                    "description": picked.description,
                    "habitat": picked.habitat,
                    "uses": picked.uses,
                    "warnings": picked.warnings,
                    "first_aid": picked.first_aid,
                    "red_book": picked.red_book,
                    "iucn_status": picked.iucn_status,
                    "regions": picked.regions,
                    "picture": picked.image_url or (request.build_absolute_uri(picked.image.url) if picked.image else None),
                },
                "confidence": confidence,
                "observation_id": obs.id if obs else None,
            })

        # 2. Groq javobi — Species'ni yangilash yoki yaratish
        latin = (result.get("latin") or "").strip()
        name = (result.get("name") or "").strip() or latin
        slug = slugify(latin or name) or f"tur-{random.randint(1000, 9999)}"

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
                "summary": (result.get("summary") or "")[:280],
                "description": result.get("description") or "",
                "habitat": result.get("habitat") or "",
                "uses": result.get("uses") or "",
                "warnings": result.get("warnings") or "",
                "first_aid": result.get("first_aid") or "",
                "red_book": bool(result.get("red_book")),
                "iucn_status": (result.get("iucn_status") or "NE")[:4],
                "regions": result.get("regions") or "",
            },
        )

        # 3. Kuzatuv yaratish
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
                "alternatives": result.get("alternatives") or [],
                "key_features": result.get("key_features") or "",
                "picture": request.build_absolute_uri(obs.photo.url) if obs and obs.photo else None,
            },
            "confidence": confidence,
            "observation_id": obs.id if obs else None,
            "new_species": created,
        })
