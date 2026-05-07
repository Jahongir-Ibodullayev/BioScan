"""Custom admin views — push broadcast, stats dashboard."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html

User = get_user_model()


class BioScanAdminSite(admin.AdminSite):
    site_header = "BioScan Boshqaruv"
    site_title = "BioScan admin"
    index_title = "BioScan boshqaruv paneli"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("push-broadcast/", self.admin_view(self.push_broadcast),
                 name="push-broadcast"),
            path("stats/", self.admin_view(self.stats_view), name="stats"),
        ]
        return my_urls + urls

    def push_broadcast(self, request):
        """Send push notification to all users with FCM token."""
        from accounts.push import send_push_bulk
        result = None
        if request.method == "POST":
            title = request.POST.get("title", "").strip()
            body = request.POST.get("body", "").strip()
            tokens = list(
                User.objects.exclude(fcm_token="")
                    .values_list("fcm_token", flat=True)
            )
            if title and body and tokens:
                count = send_push_bulk(tokens, title, body)
                result = f"✓ {count}/{len(tokens)} ta yuborildi"
            elif not tokens:
                result = "Hozir push qabul qiladigan foydalanuvchilar yo'q"
            else:
                result = "Sarlavha va matn talab qilinadi"
        ctx = {
            **self.each_context(request),
            "title": "Push xabar yuborish",
            "result": result,
            "user_count": User.objects.exclude(fcm_token="").count(),
        }
        return render(request, "admin/push_broadcast.html", ctx)

    def stats_view(self, request):
        """Quick numbers."""
        from observations.models import Observation
        from catalog.models import Species
        from shop.models import Product, Order
        ctx = {
            **self.each_context(request),
            "title": "Statistika",
            "users_total": User.objects.count(),
            "users_with_telegram": User.objects.exclude(telegram_id=None).count(),
            "users_with_fcm": User.objects.exclude(fcm_token="").count(),
            "species_total": Species.objects.count(),
            "species_redbook": Species.objects.filter(red_book=True).count(),
            "scans_total": Observation.objects.count(),
            "products_total": Product.objects.count(),
            "orders_total": Order.objects.count() if hasattr(Order, "objects") else 0,
        }
        return render(request, "admin/stats.html", ctx)
