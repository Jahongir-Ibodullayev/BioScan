from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "text", "created_at")
        read_only_fields = ("id", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "created_at", "messages")
        read_only_fields = ("id", "created_at")


class AskSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False)
    text = serializers.CharField(max_length=2000)
