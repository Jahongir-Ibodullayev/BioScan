from rest_framework import permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from catalog.models import Species
from togai.integrations import groq_chat
from togai.throttles import AIChatThrottle

from .models import Conversation, Message
from .serializers import AskSerializer, ConversationSerializer, MessageSerializer

def answer_for(text: str) -> str:
    """Real AI javob — Groq LLM orqali, BioScan flora/fauna konteksti bilan."""
    system = (
        "Sen BioScan yordamchisisan — Markaziy Osiyo (asosan O'zbekiston) tabiati, "
        "o'simlik, jonivor, qush, hasharot, qoziqorin va xavfli holatlar bo'yicha ekspert. "
        "Javobni FAQAT o'zbek tilida, qisqa va aniq (2-4 jumla) ber. "
        "Bilmasang tan ol — yolg'on yozma, foydalanuvchi sog'lig'iga zarar bo'lishi mumkin. "
        "Ilon chaqishi, zaharlanish kabi favqulodda holatlarda 103 raqamiga qo'ng'iroq qilishni eslatib o't."
    )
    try:
        return groq_chat(text, system=system)
    except Exception:
        return "Hozir AI bilan bog'lana olmadim. Bir oz vaqtdan keyin qayta urinib ko'ring."


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Conversation.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        return Conversation.objects.filter(user=self.request.user).prefetch_related("messages")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"])
    def ask(self, request):
        """POST /api/chat/conversations/ask/  {conversation_id?, text}
        → yangi/mavjud suhbat'ga xabar qo'shadi, AI javobini qo'shadi."""
        ser = AskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        conv_id = ser.validated_data.get("conversation_id")
        if conv_id:
            conv = Conversation.objects.filter(id=conv_id, user=request.user).first()
            if not conv:
                return Response({"detail": "Suhbat topilmadi"}, status=404)
        else:
            conv = Conversation.objects.create(user=request.user, title=ser.validated_data["text"][:60])

        user_msg = Message.objects.create(
            conversation=conv, role=Message.ROLE_USER, text=ser.validated_data["text"]
        )
        ai_reply = answer_for(ser.validated_data["text"])
        ai_msg = Message.objects.create(conversation=conv, role=Message.ROLE_AI, text=ai_reply)

        return Response(
            {
                "conversation_id": conv.id,
                "messages": MessageSerializer([user_msg, ai_msg], many=True).data,
            }
        )


UZ_FLORA_FAUNA = """MARKAZIY OSIYO FLORA/FAUNA LUG'ATI (majburiy — bu ro'yxatdagi so'zlarni to'g'ri talqin qil):

O'SIMLIKLAR (GIYOH/DARAXT):
• Yantoq = Alhagi pseudoalhagi — tikanli buta o'simlik (CAMEL THORN), QUSH EMAS!
  Xususiyatlari: oshqozon-ichak, buyrak, jigar davolash, siydik haydovchi, asalbop.
• Isiriq (Hazorasfand) = Peganum harmala — alkaloid saqlovchi o'simlik, tutatib tozalash.
• Shuvoq = Artemisia — achchiq dorivor giyoh, oshqozon davolash.
• Yalpiz = Mentha — ya'lizli dorivor o'simlik.
• Na'matak = Rosa canina — C vitamini manbai.
• Qoqio't = Taraxacum (dandelion) — jigar, buyrak profilaktikasi.
• Archa = Juniperus — ignabargli daraxt, Markaziy Osiyo tog'larida.
• Saksovul = Haloxylon — cho'l butasi.
• Chakanda = Hippophae — dengiz buta mevasi, vitamin bomba.
• Zirk = Berberis — sariq ildiz, qizil meva.
• Qirqbo'g'im = Equisetum — tomirli giyoh.
• Tuya tovon = Tussilago — tikan yo'l o'simlik.
• Ismaloq = Spinacia — ovqatbop sabzavot.

JONIVORLAR:
• Tog' qo'yi (Arxar) = Ovis ammon — yirik tog' hayvoni.
• Qor qoploni = Panthera uncia — yo'q bo'lib borayotgan mushuksimon.
• Jayron = Gazella subgutturosa — cho'l antilopasi.
• Qunduz = Castor — suv bo'yi hayvoni.

ILONLAR (xavfli):
• Gurza (ko'za ilon) = Macrovipera lebetina — eng xavfli, zahari kuchli.
• Efa = Echis carinatus — kichik, juda xavfli.
• Kobra (Osiyo kobrasi) = Naja oxiana — qalpoqli, zaharli.
• Qum bog'mauchi = Eryx — zahari yo'q.

QUSHLAR:
• Burgut = Aquila — yirik yirtqich qush.
• Chittak = Parus — kichik qo'shiqchi qush.
• Zag'izg'on = Corvus monedula — qora qush.

QOIDA: agar mavzu shu ro'yxatda bo'lmasa va aniq bilmasang, "Bu haqda aniq ma'lumotim yo'q,
yaqin kunlarda bazam yangilanadi" deb ayt. HECH QACHON TAXMIN QILMA VA YOLG'ON YOZMA!"""


def _find_species_in_text(text: str):
    """Fuzzy search: return first Species matching any keyword in text."""
    t = text.lower()
    # split into words of length >=3
    words = [w.strip(".,?!:;'\"()") for w in t.split() if len(w) >= 3]
    for w in words:
        sp = Species.objects.filter(name__icontains=w).first()
        if sp:
            return sp
        sp = Species.objects.filter(latin__icontains=w).first()
        if sp:
            return sp
    return None


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AIChatThrottle])
def ai_public(request):
    """POST /api/chat/ai/  {text, species_slug?}
    Public AI — no auth, no persistence. Fast path for Scan→Chat flow.
    """
    text = (request.data.get("text") or "").strip()
    if not text:
        return Response({"detail": "text bo'sh bo'lmasin"}, status=400)

    # Try explicit species from scanner context first, then fuzzy-match question text
    sp = None
    slug = request.data.get("species_slug")
    if slug:
        sp = Species.objects.filter(slug=slug).first()
    if not sp:
        sp = _find_species_in_text(text)

    context_block = ""
    if sp:
        context_block = (
            f"\n\nAUTORITATIV KONTEKST (bazamizdan):\n"
            f"Nom: {sp.name}\n"
            f"Lotin: {sp.latin}\n"
            f"Kategoriya: {sp.category}\n"
            f"Tavsif: {sp.description or sp.summary or '—'}\n"
            f"Foydasi: {sp.uses or '—'}\n"
            f"Xavfi: {sp.warnings or '—'}\n"
            f"Qizil kitob: {'HA' if sp.red_book else 'yoq'}\n"
            f"→ Javobingda shu ma'lumotdan foydalan."
        )

    system = (
        "Sen BioScan yordamchisisan — Markaziy Osiyo flora/faunasi bo'yicha ekspert biologist. "
        "O'zbek tilida, qisqa (3-5 jumla), aniq, amaliy javob ber. "
        "Xavfli mavzularda ehtiyot choralarini ham ko'rsat.\n\n"
        + UZ_FLORA_FAUNA
    )
    prompt = f"Savol: {text}{context_block}"
    reply = groq_chat(prompt, system=system)
    return Response({"reply": reply})
