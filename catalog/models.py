from django.db import models


class Category(models.TextChoices):
    PLANT = "giyoh", "Giyoh"
    TREE = "daraxt", "Daraxt"
    FLOWER = "gul", "Gul"
    ANIMAL = "jonivor", "Jonivor"
    INSECT = "hasharot", "Hasharot"
    BIRD = "qush", "Qush"
    FUNGUS = "qoziqorin", "Qoziqorin"


class IUCNStatus(models.TextChoices):
    LC = "LC", "Least Concern"
    NT = "NT", "Near Threatened"
    VU = "VU", "Vulnerable"
    EN = "EN", "Endangered"
    CR = "CR", "Critically Endangered"
    EW = "EW", "Extinct in Wild"
    EX = "EX", "Extinct"
    DD = "DD", "Data Deficient"
    NE = "NE", "Not Evaluated"


class Species(models.Model):
    slug = models.SlugField(max_length=140, unique=True)
    name = models.CharField(max_length=140, db_index=True)
    latin = models.CharField(max_length=160, blank=True)
    category = models.CharField(max_length=16, choices=Category.choices, db_index=True)
    icon_name = models.CharField(
        max_length=40,
        default="leaf",
        help_text="Frontend icon key: leaf, tree, flower, snake, paw, bird...",
    )
    color_class = models.CharField(
        max_length=80,
        default="bg-primary-100 text-primary-700",
        help_text="Tailwind class for tile background",
    )

    summary = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    habitat = models.TextField(blank=True)
    uses = models.TextField(blank=True)
    warnings = models.TextField(blank=True)
    first_aid = models.TextField(blank=True)

    image = models.ImageField(upload_to="species/", null=True, blank=True)
    image_url = models.URLField(blank=True, max_length=600, help_text="Optional external image (Unsplash, Wikipedia)")

    red_book = models.BooleanField(default=False, db_index=True, help_text="Mahalliy Qizil kitobda")
    iucn_status = models.CharField(
        max_length=4, choices=IUCNStatus.choices, default=IUCNStatus.NE, db_index=True,
    )

    regions = models.CharField(
        max_length=240,
        blank=True,
        help_text="Mintaqa(lar), vergul bilan: 'Shahrisabz, G'arbiy Tyan-Shan'",
    )
    external_ref = models.URLField(
        blank=True, help_text="iNaturalist / GBIF / Wikipedia havolasi"
    )

    # ====== YANGI filter field'lar (V3) ======
    halal_status = models.CharField(
        max_length=10, default="unknown", db_index=True,
        help_text="halal | makruh | haram | unknown",
    )
    is_medicinal = models.BooleanField(default=False, db_index=True, help_text="Dorivor giyohmi?")
    is_honey_plant = models.BooleanField(default=False, db_index=True, help_text="Asalari uchun yaxshi?")
    livestock_danger = models.CharField(
        max_length=10, default="safe", db_index=True,
        help_text="safe | toxic | deadly",
    )
    is_edible = models.BooleanField(default=False, db_index=True)
    bloom_months = models.CharField(
        max_length=50, blank=True,
        help_text="Gulash oylari (vergul bilan): 4,5,6",
    )
    harvest_months = models.CharField(max_length=50, blank=True)

    # Law / Red Book extended
    fine_bhm_min = models.IntegerField(default=0)
    fine_bhm_max = models.IntegerField(default=0)
    law_article = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tur"
        verbose_name_plural = "Turlar"
        ordering = ("name",)
        indexes = [
            models.Index(fields=["category", "red_book"], name="sp_cat_redbook_idx"),
            models.Index(fields=["category", "is_medicinal"], name="sp_cat_med_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.latin})" if self.latin else self.name

    @property
    def picture(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url
