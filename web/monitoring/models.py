from django.db import models

class Machine(models.Model):
    machine_name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'machines'
        verbose_name = 'Machine'
        verbose_name_plural = 'Machines'

    def __str__(self):
        return self.machine_name

class TagConfig(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='tags', db_column='machine_id')
    tag_name = models.CharField(max_length=255)
    opc_address = models.CharField(max_length=500, unique=True)
    is_active = models.BooleanField(default=True)
    deadband = models.FloatField(default=0)
    update_interval = models.IntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tag_config'
        verbose_name = 'Tag Configuration'
        verbose_name_plural = 'Tag Configurations'

    def __str__(self):
        return f"{self.machine.machine_name} - {self.tag_name}"

class TagLatestSnapshot(models.Model):
    tag = models.OneToOneField(TagConfig, on_delete=models.CASCADE, primary_key=True, db_column='tag_id')
    last_value = models.TextField(blank=True, null=True)
    last_status = models.CharField(max_length=100, blank=True, null=True)
    last_update = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'tag_latest_snapshot'
        verbose_name = 'Tag Snapshot'
        verbose_name_plural = 'Tag Snapshots'

class RawDataPool(models.Model):
    tag = models.ForeignKey(TagConfig, on_delete=models.CASCADE, db_column='tag_id')
    tag_value = models.TextField(blank=True, null=True)
    status_code = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'raw_data_pool'
        verbose_name = 'Raw Data'
        verbose_name_plural = 'Raw Data'
        ordering = ['-timestamp']
