"""
Models for the Logistics Intelligence Dashboard.

Normalized models:
  - Route:     Unique origin→destination pairs
  - UploadLog: Tracks every file upload with processing stats + data quality
  - Shipment:  Core shipment records with financial, weight, transit, quality,
               POD upload, and driver assignment fields
"""

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator


class Route(models.Model):
    """
    Normalized representation of a shipping route.
    A route is a unique (origin, destination) pair.
    """

    origin = models.CharField(max_length=255, db_index=True)
    destination = models.CharField(max_length=255, db_index=True)

    class Meta:
        unique_together = ("origin", "destination")
        ordering = ["origin", "destination"]
        indexes = [
            models.Index(fields=["origin", "destination"], name="idx_route_pair"),
        ]

    def __str__(self):
        return f"{self.origin} → {self.destination}"

    @property
    def label(self):
        return f"{self.origin} → {self.destination}"


class UploadLog(models.Model):
    """
    Audit trail for every file upload.
    Tracks processing outcomes and data quality score.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial Success"

    file_name = models.CharField(max_length=512)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    error_log = models.TextField(
        blank=True,
        default="",
        help_text="JSON-formatted log of row-level errors",
    )
    processing_time_ms = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Total processing time in milliseconds",
    )
    # Data quality score (0–100) for this upload
    data_quality_score = models.IntegerField(
        default=0,
        help_text="Data quality score 0–100 for this upload batch",
    )
    quality_issues = models.TextField(
        blank=True, default="",
        help_text="JSON list of quality issues found",
    )
    original_file = models.FileField(
        upload_to="uploads/%Y/%m/",
        null=True, blank=True,
        help_text="The source data file (Excel or CSV)",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="uploads",
        help_text="The manager who uploaded this data",
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Upload #{self.pk}: {self.file_name} ({self.status})"


class Shipment(models.Model):
    """
    Core shipment record.
    Contains raw data plus derived/computed fields.

    Financial fields: total_amount, rate_per_mt, freight_deduction, penalty, amount_receivable
    Weight fields: net_weight, gross_weight, charge_weight, shortage
    Transit fields: transit_permissible, transit_taken, delay_days, is_on_time
    """

    # --- Identity ---
    shipment_id = models.CharField(
        max_length=100, unique=True, db_index=True,
        help_text="Unique shipment identifier (C/N No.) from source data",
    )

    # --- Relationships ---
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name="shipments",
    )
    upload = models.ForeignKey(
        UploadLog, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="shipments",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="shipments",
        help_text="Owner of the shipment record",
    )

    # --- Dates ---
    dispatch_date = models.DateField(db_index=True)
    delivery_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)

    # --- Vehicle ---
    vehicle_type = models.CharField(max_length=50, db_index=True, default="other")
    vehicle_no = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Vehicle registration number",
    )

    # --- Financial ---
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0,
    )
    rate_per_mt = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Rate per metric ton",
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Gross billing amount",
    )
    freight_deduction = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Freight deduction amount",
    )
    penalty = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Late delivery penalty amount",
    )
    amount_receivable = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Net amount receivable after deductions",
    )

    # --- Driver Info (New) ---
    driver_name = models.CharField(max_length=255, blank=True, default="")
    driver_phone = models.CharField(max_length=20, blank=True, default="")

    # --- Weight ---
    net_weight = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
        help_text="Net weight in metric tons",
    )
    gross_weight = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
    )
    charge_weight = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
    )
    shortage = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
        help_text="Shortage in metric tons",
    )

    # --- Transit (computed) ---
    transit_permissible = models.IntegerField(
        default=0, help_text="Permissible transit time in days (SLA)",
    )
    transit_taken = models.IntegerField(
        default=0, help_text="Actual transit time in days",
    )
    delay_days = models.IntegerField(
        default=0, help_text="transit_taken - transit_permissible",
    )
    is_on_time = models.BooleanField(default=True, db_index=True)

    # --- Flags (derived) ---
    has_shortage = models.BooleanField(
        default=False, db_index=True,
        help_text="True if shortage > 0",
    )
    has_penalty = models.BooleanField(
        default=False, db_index=True,
        help_text="True if penalty > 0",
    )

    # --- Advanced Tracking (SAP Extensions) ---
    total_distance = models.FloatField(
        null=True, blank=True, help_text="Total transit distance in km",
    )
    pod_status = models.CharField(
        max_length=50, blank=True, default="", help_text="Status of the Proof of Delivery",
    )
    billing_status = models.CharField(
        max_length=50, blank=True, default="", help_text="Status of the Billing",
    )

    # --- Domain Entities ---
    customer_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    transporter_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    booking_region = models.CharField(max_length=100, blank=True, default="")
    contract_id = models.CharField(max_length=100, blank=True, default="")
    material_type = models.CharField(max_length=150, blank=True, default="")
    consignor_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    consignee_name = models.CharField(max_length=255, blank=True, default="", db_index=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dispatch_date"]
        indexes = [
            models.Index(fields=["dispatch_date", "is_on_time"], name="idx_dispatch_ontime"),
            models.Index(fields=["vehicle_type", "dispatch_date"], name="idx_vehicle_dispatch"),
            models.Index(fields=["delivery_date"], name="idx_delivery_date"),
            models.Index(fields=["has_shortage"], name="idx_has_shortage"),
            models.Index(fields=["has_penalty"], name="idx_has_penalty"),
        ]

    def __str__(self):
        status = "on-time" if self.is_on_time else f"delayed {self.delay_days}d"
        return f"Shipment {self.shipment_id} ({status})"


class ProfitRecord(models.Model):
    """
    Stores Gross Margin Fusion MIS data for Profit Analysis.
    Each record represents a single consignment with full margin breakdown (GM1→GM7).
    """

    # --- Identity ---
    sap_delivery_no = models.CharField(
        max_length=100, db_index=True,
        help_text="SAP Delivery Number — primary identifier from MIS report",
    )

    # --- Relationships ---
    upload = models.ForeignKey(
        UploadLog, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="profit_records",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="profit_records",
    )

    # --- Dates ---
    cn_date = models.DateField(db_index=True, help_text="Consignment date")
    pod_date = models.DateField(null=True, blank=True, help_text="Proof of delivery date")

    # --- Location / Route ---
    booking_branch = models.CharField(max_length=255, blank=True, default="")
    loading_state = models.CharField(max_length=255, blank=True, default="", db_index=True)
    loading_city = models.CharField(max_length=255, blank=True, default="", db_index=True)
    delivery_state = models.CharField(max_length=255, blank=True, default="")
    delivery_city = models.CharField(max_length=255, blank=True, default="", db_index=True)

    # --- Entities ---
    customer_name = models.CharField(max_length=512, blank=True, default="")
    consignor = models.CharField(max_length=512, blank=True, default="")
    consignee_name = models.CharField(max_length=512, blank=True, default="")
    service_agent = models.CharField(max_length=255, blank=True, default="")
    contract_owner = models.CharField(max_length=255, blank=True, default="")

    # --- Cargo ---
    vehicle_type = models.CharField(max_length=100, blank=True, default="")
    material_name = models.CharField(max_length=255, blank=True, default="")
    contract_type = models.CharField(max_length=100, blank=True, default="")
    gross_weight = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    net_weight = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    charge_weight = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    distance = models.IntegerField(default=0)
    value_of_goods = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # --- Revenue ---
    freight = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # --- Costs ---
    fleet_freight = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lorry_hire = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lorry_hire_topf = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    own_fleet_exp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    rake_exp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    freight_deduction = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    extra_lorry_hire = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transhipment_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # --- Margin Tier 1 (GM1 = Freight - Direct Transport Costs) ---
    gm1 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm1_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    # --- Operational Adjustments ---
    freight_incentive = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    operational_other_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    labour = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    wages = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    insurance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_direct_exp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lrp = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # --- Margin Tiers 2-7 ---
    gm2 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm2_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    reimb_exp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm3 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    claim = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    detention = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ldp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_operation_ded = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm4 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    interest = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm5 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm5_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cash_discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transaction_charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pli = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    broker_discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    petro_incentive = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm6 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gm6_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    gm7 = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    projected_margin = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cn_date"]
        indexes = [
            models.Index(fields=["cn_date", "loading_city", "delivery_city"], name="idx_profit_lane_date"),
            models.Index(fields=["loading_city", "delivery_city"], name="idx_profit_lane"),
        ]

    def __str__(self):
        return f"Profit {self.sap_delivery_no} ({self.loading_city}→{self.delivery_city})"

    @property
    def lane_name(self):
        return f"{self.loading_city} → {self.delivery_city}"

    @property
    def total_cost(self):
        return float(self.lorry_hire) + float(self.lorry_hire_topf) + float(self.fleet_freight) + \
               float(self.own_fleet_exp) + float(self.rake_exp) + float(self.extra_lorry_hire) + \
               float(self.transhipment_cost)

    @property
    def cost_per_tonne(self):
        w = float(self.charge_weight)
        return self.total_cost / w if w > 0 else 0
