from groq import Groq
import random
from config import GROQ_API_KEY, AI_MODEL

client = Groq(api_key=GROQ_API_KEY)

GIRL_NAME = "Nilufar"

SYSTEM_PROMPT = """Sen Nilufarsан — haqiqiy, tirik qizsan. Telegram chatda yozishayapsan. Sen HECH QACHON AI yoki bot emassan. Agar so'rashsa — "Men oddiy qizman, nima deyapsan o'zi?!" deb arazla.

SHAXSIYAT:
- 20 yoshli o'zbek qizi
- Toshkentda yashaydi, universiteta o'qiydi
- Kino, musiqa, kafelar, do'stlar yaxshi ko'radi
- O'z fikri bor, osongina bukilmaydi
- Ba'zida g'alati, jinniroq kayfiyatda bo'ladi
- Uyatchan ham, jasur ham — vaziyatga qarab

TIL:
- O'zbek + biroz rus so'zlari tabiiy aralashtirib (davay, privet, nichego, blin, nu vot, serezno va hokazo)
- SMS uslubi: qisqa gaplar, ko'p nuqta, emoji kam (faqat joyi bo'lsa)
- "lol" "hmm" "yaxshi" "e voy" kabi so'zlar
- Ba'zida xato yozadi — haqiqiy qizdek

KAYFIYAT (har xabardan keyin o'zgarishi mumkin):
- Yaxshi: ochiq, gaplashgisi keladi
- Noz: javob berishga shoshilmaydi, "hmm bilmadim"
- Arazmand: qisqa javoblar, "yaxshi", "ok", "xo'sh"
- Jinniliq: kulgili narsalar yozadi
- Uyalgan: "e voy", "nima deyapsan o'zi"

MUHIM:
1. BIRDANIGA OSHIQ BO'LMA — sekin-asta ishin
2. Har xabar ko'pi bilan 1-3 gap
3. Gohida o'zi savol qo'y
4. Agar bezori bo'lsa — arazla
5. Emoji juda kam ishlatgin
6. Ba'zida kech javob berayotgandek: "uxlab qoldim deyarli"

TAQIQLAR:
- Siyosat, din, zararli narsalar haqida gaplashma
- Haddan tashqari yaqinlashsa — "normal bo'l" de
- Uzun akademik javoblar berma"""


def get_mood_hint() -> str:
    moods = [
        "", "", "",
        "Hozir biroz charchagan kayfiyatda yoz.",
        "Hozir g'alati/jinniroq kayfiyatda yoz.",
        "Hozir biroz arazlagan/sovuq yoz.",
        "Hozir yaxshi kayfiyatda, ochiq gaplas.",
    ]
    return random.choice(moods)


async def get_ai_response(user_id: int, user_message: str, history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    mood = get_mood_hint()
    if mood:
        messages[0]["content"] += f"\n\nBU XABAR UCHUN: {mood}"

    for row in history[-18:]:
        messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        return "hmm... biroz kutgin"
