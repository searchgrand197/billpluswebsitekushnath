from django.db import models

# Create your models here.

class Slideshow(models.Model):
    image = models.ImageField(upload_to='slideshows/', blank=True, null=True)
    video = models.FileField(upload_to='slideshows/', blank=True, null=True)
    mobile_image = models.ImageField(
        upload_to='slideshows/',
        blank=True,
        null=True,
        help_text='Optional portrait/mobile image (recommended ~9:16 or 3:4).',
    )
    mobile_video = models.FileField(
        upload_to='slideshows/',
        blank=True,
        null=True,
        help_text='Optional portrait/mobile video. Falls back to desktop video if empty.',
    )
    headline = models.CharField(max_length=200)
    tagline = models.CharField(max_length=500)
    link = models.URLField(blank=True, null=True)
    button_text = models.CharField(max_length=200, default='Learn More')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Slideshow'
        verbose_name_plural = 'Slideshows'

    def __str__(self):
        return self.headline

    @property
    def has_mobile_media(self):
        return bool(self.mobile_video or self.mobile_image)
