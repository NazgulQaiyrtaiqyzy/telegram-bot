import json
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from google import genai
from APITOKEN import API_KEY, TOKEN

# -------------------------------
# GEMINI БАПТАУ
# -------------------------------
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "models/gemini-flash-latest"

# -------------------------------
# МҰҒАЛІМ ID
# -------------------------------
TEACHER_IDS = [928328657]

# -------------------------------
# ТАПСЫРМАЛАР (ӨЗГЕРМЕГЕН)
# -------------------------------
topics = {
    "input_print": [
        "input() арқылы пайдаланушыдан сан енгізіп, оны print() арқылы шығарыңыз.",
        "Пайдаланушыдан екі сан сұрап, оларды қосып шығарыңыз.",
        "Пайдаланушыдан аты-жөнін сұрап, сәлемдесу шығарыңыз."
    ],
    "types": [
        "int, float және str типтерін көрсететін үш айнымалы жасаңыз.",
        "Санды str типіне айналдырып print() арқылы шығарыңыз.",
        "float санды int типіне айналдырып шығарыңыз."
    ],
    "if_else": [
        "Егер сан 10-нан үлкен болса, 'Үлкен' деп шығарыңыз, әйтпесе 'Кіші'.",
        "Егер сөз 'hello' болса, 'Сәлем' деп шығарыңыз, әйтпесе 'Қош'.",
        "Егер сан жұп болса, 'Жұп', тақ болса 'Тақ' деп шығарыңыз."
    ],
    "for_loop": [
        "for циклін қолданып 1-ден 5-ке дейінгі сандарды шығарыңыз.",
        "for арқылы тізімдегі әр элементті шығарыңыз.",
        "for циклін қолданып әріптер тізімін шығарыңыз."
    ],
    "while_loop": [
        "while циклін қолданып 0-ден 3-ке дейін санаңыз.",
        "while арқылы 5-тен 0-ге дейін санап шығыңыз.",
        "while арқылы пайдаланушы 'stop' деп жазғанша сұраңыз."
    ],
    "list_array": [
        "Тізім (list) құрып, үш элемент қосып, print() арқылы көрсетіңіз.",
        "for арқылы тізімдегі элементтерді шығарыңыз.",
        "list-ке жаңа элемент қосып, соңында print() арқылы шығарыңыз."
    ],
    "simple_array_tasks": [
        "Массивтен (list) бірінші элементті print() арқылы шығарыңыз.",
        "Массивке жаңа элемент қосып, print() арқылы көрсетіңіз.",
        "Массивтің ұзындығын len() арқылы шығарыңыз."
    ]
}

# -------------------------------
# ЖИ АРҚЫЛЫ ТЕКСЕРУ (ТҮЗЕТІЛГЕН)
# -------------------------------
async def ai_check(topic, task, answer):
    prompt = f"""
Сен Python мұғалімісің.
Тақырып: {topic}
Тапсырма: {task}
Студент жауабы: {answer}

Тексеріп, ТЕК JSON қайтар:
{{"correct": true/false, "score": 1 немесе 0, "comment": "қысқа пікір"}}
"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=prompt
        )

        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    except Exception as e:
        print("AI Error:", e)
        return {
            "correct": False,
            "score": 0,
            "comment": "ЖИ тексеру кезінде қате шықты"
        }

# -------------------------------
# НӘТИЖЕЛЕРДІ ЖҮКТЕУ
# -------------------------------
if os.path.exists("students_results.json"):
    with open("students_results.json", "r", encoding="utf-8") as f:
        students_results = json.load(f)
else:
    students_results = {}

user_data = {}

# -------------------------------
# START
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Сәлем! Аты-жөніңізді енгізіңіз:")
    user_data[update.effective_chat.id] = {"step": "get_name"}

# -------------------------------
# ХАБАРЛАМА ХЕНДЛЕР
# -------------------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id not in user_data:
        return

    user = user_data[chat_id]

    if user["step"] == "get_name":
        user["name"] = text
        user["topics_list"] = list(topics.keys())
        user["topic_index"] = 0
        user["task_index"] = 0
        user["results"] = {}
        user["step"] = "task"

        topic = user["topics_list"][0]
        user["results"][topic] = []
        await update.message.reply_text(
            f"Сәлем, {text}!\n\nТапсырма:\n{topics[topic][0]}"
        )
        return

    if user["step"] == "task":
        topic = user["topics_list"][user["topic_index"]]
        task = topics[topic][user["task_index"]]

        ai_res = await ai_check(topic, task, text)
        user["results"][topic].append(ai_res["score"])

        await update.message.reply_text(f"🤖 ЖИ: {ai_res['comment']}")

        user["task_index"] += 1

        if user["task_index"] < len(topics[topic]):
            await update.message.reply_text(
                f"Келесі тапсырма:\n{topics[topic][user['task_index']]}"
            )
        else:
            avg = sum(user["results"][topic]) / len(user["results"][topic])
            level = "Жақсы" if avg >= 0.7 else "Орташа"

            students_results.setdefault(user["name"], {})[topic] = {
                "score": avg,
                "level": level
            }

            with open("students_results.json", "w", encoding="utf-8") as f:
                json.dump(students_results, f, ensure_ascii=False, indent=4)

            user["topic_index"] += 1
            user["task_index"] = 0

            if user["topic_index"] < len(user["topics_list"]):
                next_topic = user["topics_list"][user["topic_index"]]
                user["results"][next_topic] = []
                await update.message.reply_text(
                    f"Келесі тақырып: {next_topic}\nТапсырма:\n{topics[next_topic][0]}"
                )
            else:
                await update.message.reply_text("Барлық тапсырмалар аяқталды ✅")
                user["step"] = "done"

# -------------------------------
# ЕСЕП
# -------------------------------
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in TEACHER_IDS:
        await update.message.reply_text("Рұқсат жоқ ❌")
        return

    text = ""
    for name, data in students_results.items():
        text += f"\n{name}:"
        for t, d in data.items():
            text += f"\n - {t}: {round(d['score']*100)}%"

    prompt = f"Мына нәтижелерге мұғалімге арналған қазақша анализ жаса:\n{text}"

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_NAME,
        contents=prompt
    )

    await update.message.reply_text(response.text)

# -------------------------------
# ІСКЕ ҚОСУ
# -------------------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот қосылды...")
    app.run_polling()
