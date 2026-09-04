from django.core.management.base import BaseCommand
from dashboard.models import Company

class Command(BaseCommand):
    help = 'Create default company record'

    def handle(self, *args, **options):
        if not Company.objects.exists():
            company = Company.objects.create(
                name="Kushnath Ayurveda",
                tagline="THE PURITY OF NATURE",
                description="Leading provider of authentic Ayurvedic products and natural remedies",
                address="Your Company Address Here",
                phone="+91-XXXXXXXXXX",
                email="info@kushnathayurveda.com",
                website="https://kushnathayurveda.com"
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created company: {company.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Company record already exists')
            )
