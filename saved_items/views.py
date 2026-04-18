from rest_framework import permissions, viewsets

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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
