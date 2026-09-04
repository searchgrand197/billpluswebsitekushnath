from rest_framework import serializers
from .models import Slideshow

class SlideshowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slideshow
        fields = [
            'id', 'image', 'video', 'headline', 'tagline', 'link',
            'button_text', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at'] 