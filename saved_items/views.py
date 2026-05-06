from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .models import SavedSpecies
from .serializers import SavedSpeciesSerializer


class SavedSpeciesViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSpeciesSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SavedSpecies.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SavedSpecies.objects.none()
        return SavedSpecies.objects.filter(user=self.request.user).select_related("species")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        species = serializer.validated_data["species"]
        note = serializer.validated_data.get("note", "")
        obj, created = SavedSpecies.objects.get_or_create(
            user=request.user,
            species=species,
            defaults={"note": note},
        )
        if not created and note and obj.note != note:
            obj.note = note
            obj.save(update_fields=["note"])
        data = self.get_serializer(obj).data
        return Response(
            data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
