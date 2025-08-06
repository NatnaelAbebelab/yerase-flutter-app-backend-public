from rest_framework import serializers

from admins.models import Audiobook
from .models import *

class CustomerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']
        read_only_fields = ['id', 'username']

class CustomerUsersAccountSerializer(serializers.ModelSerializer):
    user = CustomerAccountSerializer(read_only=True)

    class Meta:
        model = CustomUsers
        fields = [
            '_id', 'user', 'phone', 'weight', 'height', 'age', 'gender', 'profile',
            'created_by', 'created_at', 'updated_by', 'updated_at', 'record_time'
        ]

class AudiobookLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audiobook
        fields = ['_id', 'title', 'audio', 'thumbnail', 'duration']

class PlaylistSerializer(serializers.ModelSerializer):
    user = CustomerAccountSerializer(read_only=True)

    class Meta:
        model = Playlist
        fields = '__all__'

class GetAllPlaylistsSerializer(serializers.ModelSerializer):
    user = CustomerAccountSerializer(read_only=True)
    audios = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = '__all__'

    def get_audios(self, obj):
        audio_ids = obj.audios or []
        queryset = Audiobook.objects.filter(_id__in=audio_ids, is_deleted=False)
        return AudiobookLiteSerializer(queryset, many=True).data