import os
import json
import requests
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction

from conferences.models import Venue, Instance, Publication


class Command(BaseCommand):
    help = (
        "Ingest CVPR 2017 metadata JSON into Venue, Instance, and Publication tables, "
        "including downloading and storing PDFs in MinIO via the raw_file FileField, "
        "with authors stored as semicolon-separated strings and progress output."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-path", "-j",
            required=True,
            help="Path to the CVPR 2017 JSON file (array of publication dicts)"
        )
        parser.add_argument(
            "--clear-old", "-c",
            action="store_true",
            help="If set, delete any existing CVPR entries before ingesting."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        json_path = options.get('json_path') or options.get('json-path')
        clear_old = options.get('clear_old', False)

        # 1) Validate JSON file exists
        if not os.path.exists(json_path):
            raise CommandError(f"JSON file not found: {json_path}")

        # 2) Load JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON format: {e}")
        if not isinstance(records, list):
            raise CommandError("Expected a JSON array of publication objects.")

        total = len(records)
        self.stdout.write(f"🚀 Starting ingestion of {total} CVPR 2017 records...")

        # 3) Optionally clear old data
        if clear_old:
            self.stdout.write("⚠️  Clearing existing CVPR entries...")
            Venue.objects.filter(name__iexact="CVPR").delete()

        # 4) Create or get the Venue
        venue, v_created = Venue.objects.get_or_create(
            name="CVPR",
            defaults={
                'type': 'Conference',
                'description': 'IEEE/CVF Conference on Computer Vision and Pattern Recognition'
            }
        )
        if v_created:
            self.stdout.write("➕ Created Venue: CVPR")

        # 5) Create or get the 2017 Instance
        inst_defaults = {
            'start_date': date(2017, 1, 1),
            'end_date':   date(2017, 1, 1),
            'location':   '',
            'website':    '',
            'summary':    '',
        }
        instance, i_created = Instance.objects.get_or_create(
            venue=venue,
            year=2017,
            defaults=inst_defaults
        )
        if i_created:
            self.stdout.write("➕ Created Instance: CVPR 2017")

        # 6) Ingest publications with progress
        added = 0
        for idx, rec in enumerate(records, start=1):
            raw_title = rec.get('title', '').strip()
            title = raw_title[:255]
            if not title:
                self.stdout.write(f"{idx}/{total}: ⏭️ Skipped empty title")
                continue

            # Truncate other char fields to their max lengths
            orgs = (rec.get('aff', '') or '')[:255]
            tag = (rec.get('track', '') or '')[:255]
            doi = (rec.get('arxiv', '') or '')[:255]
            pdf_url = (rec.get('pdf', '') or '')[:255]

            # Prepare authors string
            raw_authors = rec.get('author', '') or rec.get('authors', '') or ''
            authors_list = [a.strip() for a in raw_authors.replace(',', ';').split(';') if a.strip()]
            authors_str = ";".join(authors_list)[:500]

            pub, p_created = Publication.objects.get_or_create(
                instance=instance,
                title=title,
                defaults={
                    'orgnizations':    orgs,
                    'publish_date':    inst_defaults['start_date'],
                    # 'summary':         (rec.get('abstract', '') or '')[:500],
                    'keywords':        (rec.get('keywords', '') or '')[:500],
                    'research_topic':  (rec.get('session', '') or '')[:500],
                    'abstract':        rec.get('abstract', ''),
                    'authors':         authors_str,
                    'tag':             tag,
                    'doi':             doi,
                    'pdf_url':         pdf_url,
                }
            )
            action = '➕ Created' if p_created else '✏️ Updated'
            self.stdout.write(f"{idx}/{total}: {action} publication: {title}")
            if p_created:
                added += 1
            else:
                # Update authors on existing record
                pub.authors = authors_str

            # 7) Download PDF and save to raw_file (FileField)
            pdf_link = rec.get('pdf', '').strip()
            if pdf_link:
                try:
                    resp = requests.get(pdf_link, timeout=30)
                    resp.raise_for_status()
                    filename = Path(pdf_link).name or f"{pub.pk}.pdf"
                    pub.raw_file.save(
                        filename,
                        ContentFile(resp.content),
                        save=False
                    )
                    self.stdout.write(f"    ✅ PDF saved for '{title}'")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"    ⚠️ Failed PDF for '{title}': {e}"
                    ))

            pub.save()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done ingesting CVPR 2017: {added}/{total} publications added."
        ))
