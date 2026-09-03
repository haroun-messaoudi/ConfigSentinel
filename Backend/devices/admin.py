from django.contrib import admin
from .models import (
    Device,
    Snapshot,
    ConfigChange,
    Alert,
    SeverityClass,
    TrackedConcept,
    DetectionProfile,
)


@admin.register(SeverityClass)
class SeverityClassAdmin(admin.ModelAdmin):
    list_display = ["name", "rank"]
    ordering = ["-rank"]


@admin.register(TrackedConcept)
class TrackedConceptAdmin(admin.ModelAdmin):
    list_display = ["name", "severity_class", "source", "created_by"]
    list_filter = ["source", "severity_class"]
    search_fields = ["name", "pattern", "description"]
    readonly_fields = ["source", "created_by"]

    def get_readonly_fields(self, request, obj=None):
        # Built-in concepts: lock everything except severity_class (admin can
        # still re-rank how severe a built-in concept is treated as).
        if obj and obj.source == "BUILTIN":
            return ["name", "description", "pattern", "source", "created_by"]
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class TrackedConceptInline(admin.TabularInline):
    model = DetectionProfile.tracked_concepts.through
    extra = 1
    verbose_name = "Tracked concept"
    verbose_name_plural = "Tracked concepts"


@admin.register(DetectionProfile)
class DetectionProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "concept_count", "device_count"]
    search_fields = ["name"]
    filter_horizontal = ["tracked_concepts"]

    def concept_count(self, obj):
        return obj.tracked_concepts.count()
    concept_count.short_description = "Tracked concepts"

    def device_count(self, obj):
        return obj.devices.count()
    device_count.short_description = "Devices using this profile"


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        "name", "hostname", "management_ip", "device_type",
        "detection_profile", "is_active", "last_poll_status", "last_polled_at",
    ]
    list_filter = ["is_active", "device_type", "last_poll_status", "detection_profile"]
    search_fields = ["name", "hostname", "management_ip"]
    readonly_fields = ["last_poll_status", "last_poll_error", "last_polled_at", "last_poll_duration_ms"]
    actions = ["pause_devices", "resume_devices"]

    def pause_devices(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Paused {updated} device(s).")
    pause_devices.short_description = "Pause selected devices"

    def resume_devices(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Resumed {updated} device(s).")
    resume_devices.short_description = "Resume selected devices"


class SnapshotInline(admin.TabularInline):
    model = Snapshot
    extra = 0
    fields = ["taken_at", "config_hash", "is_baseline"]
    readonly_fields = ["taken_at", "config_hash", "is_baseline"]
    can_delete = False
    show_change_link = True
    ordering = ["-taken_at"]
    max_num = 5  # don't flood the device page — just the recent history


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ["device", "taken_at", "is_baseline", "config_hash_short"]
    list_filter = ["is_baseline", "device"]
    readonly_fields = ["device", "taken_at", "raw_text", "config_hash", "is_baseline"]
    actions = ["promote_to_baseline_action"]

    def config_hash_short(self, obj):
        return obj.config_hash[:12]
    config_hash_short.short_description = "Hash"

    def promote_to_baseline_action(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one snapshot to promote.", level="error")
            return
        snapshot = queryset.first()
        snapshot.promote_to_baseline()
        self.message_user(request, f"Promoted snapshot {snapshot.id} to baseline for {snapshot.device}.")
    promote_to_baseline_action.short_description = "Promote selected snapshot to baseline"


@admin.register(ConfigChange)
class ConfigChangeAdmin(admin.ModelAdmin):
    list_display = [
        "device", "detected_at", "severity_class", "status",
        "matched_concepts_list", "acknowledged_at",
    ]
    list_filter = ["status", "severity_class", "device"]
    readonly_fields = [
        "device", "old_snapshot", "new_snapshot", "diff_text",
        "severity_class", "matched_concepts", "detected_at", "acknowledged_at",
    ]
    actions = ["acknowledge_changes"]

    def matched_concepts_list(self, obj):
        return ", ".join(c.name for c in obj.matched_concepts.all()) or "—"
    matched_concepts_list.short_description = "Matched concepts"

    def acknowledge_changes(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status="ACKNOWLEDGED", acknowledged_at=timezone.now())
        self.message_user(request, f"Acknowledged {updated} change(s).")
    acknowledge_changes.short_description = "Acknowledge selected changes"


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["change", "created_at", "delivered"]
    list_filter = ["delivered"]
    actions = ["mark_delivered_action"]

    def mark_delivered_action(self, request, queryset):
        updated = queryset.update(delivered=True)
        self.message_user(request, f"Marked {updated} alert(s) as delivered.")
    mark_delivered_action.short_description = "Mark selected alerts as delivered"