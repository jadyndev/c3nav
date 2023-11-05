# Generated by Django 4.2.1 on 2023-11-05 17:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mesh", "0007_nodemessage_message_type_new"),
    ]

    operations = [
        migrations.CreateModel(
            name="FirmwareBuild",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "variant",
                    models.CharField(max_length=64, verbose_name="variant name"),
                ),
                (
                    "chip",
                    models.SmallIntegerField(
                        choices=[(2, "ESP32-S2"), (5, "ESP32-C3")],
                        db_index=True,
                        verbose_name="chip",
                    ),
                ),
                (
                    "sha256_hash",
                    models.CharField(
                        max_length=64, unique=True, verbose_name="SHA256 hash"
                    ),
                ),
                (
                    "binary",
                    models.FileField(
                        null=True, upload_to="", verbose_name="firmware file"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FirmwareBuildBoard",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "board",
                    models.CharField(
                        choices=[
                            ("CUSTOM", "CUSTOM"),
                            ("ESP32_C3_DEVKIT_M_1", "ESP32-C3-DevKitM-1"),
                            ("ESP32_C3_32S", "ESP32-C3-32S"),
                            ("C3NAV_UWB_BOARD", "c3nav UWB board"),
                            ("C3NAV_LOCATION_PCB_REV_0_1", "c3nav location PCB rev0.1"),
                            ("C3NAV_LOCATION_PCB_REV_0_2", "c3nav location PCB rev0.2"),
                        ],
                        db_index=True,
                        max_length=32,
                        verbose_name="board",
                    ),
                ),
                (
                    "build",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="mesh.firmwarebuild",
                    ),
                ),
            ],
            options={
                "unique_together": {("build", "board")},
            },
        ),
        migrations.CreateModel(
            name="FirmwareVersion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "project_name",
                    models.CharField(max_length=32, verbose_name="project name"),
                ),
                (
                    "version",
                    models.CharField(
                        max_length=32, unique=True, verbose_name="firmware version"
                    ),
                ),
                (
                    "idf_version",
                    models.CharField(max_length=32, verbose_name="IDF version"),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="creation/upload date"
                    ),
                ),
                (
                    "uploader",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="Firmware",
        ),
        migrations.AlterField(
            model_name="nodemessage",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("NOOP", "noop"),
                    ("ECHO_REQUEST", "echo request"),
                    ("ECHO_RESPONSE", "echo response"),
                    ("MESH_SIGNIN", "mesh signin"),
                    ("MESH_LAYER_ANNOUNCE", "mesh layer announce"),
                    ("MESH_ADD_DESTINATIONS", "mesh add destinations"),
                    ("MESH_REMOVE_DESTINATIONS", "mesh remove destinations"),
                    ("MESH_ROUTE_REQUEST", "mesh route request"),
                    ("MESH_ROUTE_RESPONSE", "mesh route response"),
                    ("MESH_ROUTE_TRACE", "mesh route trace"),
                    ("MESH_ROUTING_FAILED", "mesh routing failed"),
                    ("CONFIG_DUMP", "dump config"),
                    ("CONFIG_HARDWARE", "hardware config"),
                    ("CONFIG_BOARD", "board config"),
                    ("CONFIG_FIRMWARE", "firmware config"),
                    ("CONFIG_UPLINK", "uplink config"),
                    ("CONFIG_POSITION", "position config"),
                    ("OTA_STATUS", "ota status"),
                    ("OTA_REQUEST_STATUS", "ota request status"),
                    ("OTA_START", "ota start"),
                    ("OTA_URL", "ota url"),
                    ("OTA_FRAGMENT", "ota fragment"),
                    ("OTA_REQUEST_FRAGMENT", "ota request fragment"),
                    ("OTA_APPLY", "ota apply"),
                    ("OTA_REBOOT", "ota reboot"),
                    ("LOCATE_REQUEST_RANGE", "locate request range"),
                    ("LOCATE_RANGE_RESULTS", "locate range results"),
                    ("LOCATE_RAW_FTM_RESULTS", "locate raw ftm results"),
                ],
                db_index=True,
                max_length=24,
                verbose_name="message type",
            ),
        ),
        migrations.AddField(
            model_name="firmwarebuild",
            name="version",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="builds",
                to="mesh.firmwareversion",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="firmwarebuild",
            unique_together={("version", "variant")},
        ),
    ]
