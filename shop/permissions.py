from rest_framework import permissions


class IsSellerOrReadOnly(permissions.BasePermission):
    """SAFE_METHODS hammaga ochiq, write — faqat seller/admin."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.account_type in ("seller", "super_admin")

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Faqat o'z mahsuloti yoki admin
        return request.user == obj.seller or request.user.account_type == "super_admin"


class IsOwnerOrAdmin(permissions.BasePermission):
    """Faqat ob'ekt egasi yoki admin kira oladi."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        owner = getattr(obj, "user", None) or getattr(obj, "customer", None)
        return owner == request.user or request.user.account_type == "super_admin"
