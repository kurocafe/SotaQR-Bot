from typing import Optional
import discord
from discord.ext import commands
import discord.ui
from discord.ui import View, Select
import sqlite3
import asyncio
import os
import aiohttp
import io
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("API_KEY")
API_HOME = os.getenv("API_HOME")
DEVELOPER_ID = int(os.getenv("DEVElOPER"))
Test_guild_id = int(os.getenv("TEST_GUILD"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

def init_db():
    conn = sqlite3.connect('survey_responses.db')
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS survey_responses(
                   user_id TEXT PRIMARY KEY, 
                   user_name TEXT,
                   responses JSON
                   )
    ''')
    conn.commit()
    conn.close()

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(1330385372454064232)  # ロールIDを指定
    if role:
        await member.add_roles(role)
        print(f"{member.name}に{role.name}ロールを付与しました。")
        
        developer = bot.get_user(DEVELOPER_ID)
        await developer.send(f"**{member.name}さん**が参加しました！")
        

# QRコード生成コマンド
@bot.tree.command(name="generate_qr", description="QRコードを作るよ！")
@discord.app_commands.describe(name="Your name to include in the QR code")
async def generate_qr(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)  # 処理に時間がかかる可能性があるため、応答を遅延させる

    user_id = interaction.user.id  # ユーザーIDを取得

    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_HOME}/{user_id}?name={name}') as response:
            if response.status == 200:
                img_data = await response.read()
                file = discord.File(io.BytesIO(img_data), filename="qr_code.png")
                
                try:
                    # DMで送信
                    await interaction.user.send(f"QRコード出来たよ! \nID: {user_id}:", file=file)
                    await interaction.followup.send("QRコードを直接あなたに送りました!", ephemeral=True)
                except discord.errors.Forbidden:
                    # DMを送信できない場合（ユーザーがDMを許可していない場合など）
                    await interaction.followup.send("QRコードが送れないです。DMは開放されていますか？", ephemeral=True)
                    # await interaction.response.send_message("I couldn't send you a DM. Please check your privacy settings and try again.", ephemeral=True)
            else:
                await interaction.followup.send("QRコードの作成に失敗しました。", ephemeral=True)

# test
user_responses = {}

# あらかじめ定義されたアンケート
SURVEY_QUESTIONS = [
    {"question": "使ってみて楽しかったですか？", "options": ["5", "4", "3", "2", "1"]},
    {"question": "役に立ちそうでしたか？", "options": ["5", "4", "3", "2", "1"]},
    {"question": "今後も使ってみたいですか？", "options": ["5", "4", "3", "2", "1"]},
    {"question": "送られてきた論文はの要約はわかりやすかったですか？", "options": ["5", "4", "3", "2", "1"]},
    {"question": "論文の内容は興味がありましたか？", "options": ["5", "4", "3", "2", "1"]},
    {"question": "もし引継ぎを行うとなった場合，このシステムでどれくらい担えると感じましたか？", "options": ["5", "4", "3", "2", "1"]},
    {"question": "Discordとの連携について，どれくらい便利だと感じましたか？" , "options": ["5", "4", "3", "2", "1"]},
    # {"question": "好きな季節は？", "options": ["春", "夏", "秋", "冬"]},
    # {"question": "好きな動物は？", "options": ["5", "4", "3", "2", "1"]},
    # ここに追加の質問を入れてください（合計10問程度）
    {"question": "実際にあなたが興味を持っている分野を教えてください．（「わからない」でもOK）", "type": "free_text"},
    {"question": "最後にこのシステムについて改善点などを教えてください．（いっぱい書いてくれたら喜びます）", "type": "free_text"},
]

class SurveyView(View):
    def __init__(self, question_index):
        super().__init__()
        self.question_index = question_index
        question = SURVEY_QUESTIONS[question_index]
        self.add_item(Select(
            placeholder="選択してください",
            options=[discord.SelectOption(label=option, value=option) for option in question["options"]],
            custom_id=f"survey_{question_index}"
        ))

class FreeTextModal(discord.ui.Modal, title="自由記述回答"):
    def __init__(self, question, question_index):
        super().__init__()
        self.question_index = question_index
        self.text_input = discord.ui.TextInput(
            label=question,
            style=discord.TextStyle.long,
            max_length=1000
        )
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        response = self.text_input.value
        print(f"User {user_id} submitted free text response for question {self.question_index}: {response}")
        
        await save_free_text_response(user_id, self.question_index, response)

        # await interaction.response.send_message("回答を受け付けました。ありがとうございます！", ephemeral=True)
        
        await send_question(interaction, self.question_index + 1)




@bot.tree.command(name="survey", description="アンケートのご協力をお願いします！")
async def survey(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    responses = get_user_responses(user_id)
    
    if responses:
        class ConfirmView(discord.ui.View):
            @discord.ui.button(label="はい", style=discord.ButtonStyle.primary)
            async def yes_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.defer()
                await button_interaction.edit_original_response(content="アンケートを始めます．", view=None)
                await send_question(button_interaction, 0)

            @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
            async def no_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(content="アンケートをキャンセルしました．", view=None)

        await interaction.response.send_message("すでにアンケートに回答されています．もう一度回答しますか？", view=ConfirmView(), ephemeral=True)
    else:
        await send_question(interaction, 0)

async def send_question(interaction, question_index):
    # 質問を送信するロジック
    if question_index >= len(SURVEY_QUESTIONS):
        await complete_survey(interaction)
    else:
        # 次の質問を送信するロジック
        if question_index < len(SURVEY_QUESTIONS):
            question = SURVEY_QUESTIONS[question_index]
            if question.get("type") == "free_text":
                class FreeTextButton(discord.ui.View):
                    @discord.ui.button(label="回答する", style=discord.ButtonStyle.primary)
                    async def button_callback(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        await button_interaction.response.send_modal(FreeTextModal(question["question"], question_index))

                # インタラクションが有効かどうかをチェック
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(f"質問 {question_index + 1}/{len(SURVEY_QUESTIONS)}:\n自由記述の回答をお願いします。以下のボタンをクリックして回答してください。", view=FreeTextButton(), ephemeral=True)
                    else:
                        print("else")
                        await interaction.response.send_message(f"質問 {question_index + 1}/{len(SURVEY_QUESTIONS)}:\n自由記述の回答をお願いします。以下のボタンをクリックして回答してください。", view=FreeTextButton(), ephemeral=True)
                except:
                    # インタラクションが無効な場合、直接メッセージを送信
                    channel = interaction.channel
                    await channel.send("自由記述の回答をお願いします。", view=FreeTextButton(), delete_after=180)
            else:
                message_content = f"質問 {question_index + 1}/{len(SURVEY_QUESTIONS)}:\n**{question['question']}**"
                view = SurveyView(question_index)
                
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(message_content, view=view, ephemeral=True)
                    else:
                        await interaction.response.send_message(message_content, view=view, ephemeral=True)
                except:
                    channel = interaction.channel
                    await channel.send(message_content, view=view, delete_after=180)
        else:
            await complete_survey(interaction)



async def save_free_text_response(user_id, question_index, response):
    conn = sqlite3.connect('survey_responses.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT responses FROM survey_responses WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    
    if result:
        responses = json.loads(result[0])
    else:
        responses = {}
    
    # 質問インデックスを使用して保存
    responses[f"free_text_{question_index}"] = response
    
    json_data = json.dumps(responses)
    cursor.execute("INSERT OR REPLACE INTO survey_responses (user_id, user_name, responses) VALUES (?, ?, ?)",
                   (str(user_id), bot.get_user(int(user_id)).name, json_data))
    
    conn.commit()
    conn.close()




@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("survey_"):
            question_index = int(custom_id.split("_")[1])
            selected_option = interaction.data["values"][0]
            
            user_id = str(interaction.user.id)
            save_response(user_id, question_index, selected_option)
            
            await interaction.response.edit_message(
                content=f"**「{SURVEY_QUESTIONS[question_index]['question']}」**に対して「{selected_option}」と回答しました。",
                view=None
            )
            
            await asyncio.sleep(0.5)
            await send_question(interaction, question_index + 1)



def save_response(user_id, question_index, response):
    conn = sqlite3.connect('survey_responses.db')
    cursor = conn.cursor()
    
    # ユーザーの既存の回答を取得
    cursor.execute("SELECT responses FROM survey_responses WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    
    if result:
        # 既存の回答がある場合、JSONをロードして更新
        responses = json.loads(result[0])
    else:
        # 新規ユーザーの場合、新しい辞書を作成
        responses = {}
    
    # 新しい回答を追加 (文字列に変換)
    responses[str(question_index)] = str(response)
    
    # user_nameを取得
    user_name = bot.get_user(int(user_id)).name

    # 更新されたJSONをデータベースに保存
    json_data = json.dumps(responses)
    cursor.execute("INSERT OR REPLACE INTO survey_responses (user_id, user_name, responses) VALUES (?, ?, ?)",
                   (str(user_id), user_name, json_data))
    
    conn.commit()
    conn.close()


def get_user_responses(user_id):
    conn = sqlite3.connect('survey_responses.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT responses FROM survey_responses WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return json.loads(result[0])
    else:
        return {}

# アンケート完了時の処理例
async def complete_survey(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    responses = get_user_responses(user_id)
    
    response_summary = "アンケート回答のまとめ:\n"
    for i, question in enumerate(SURVEY_QUESTIONS):
        answer = responses.get(f"free_text_{i}", "未回答") if question.get("type") == "free_text" else responses.get(str(i), "未回答")
        response_summary += f"Q{i+1}: {question['question']} - 回答: {answer}\n"

    async def send_message(interaction, message, ephemeral=True):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=ephemeral)
            else:
                await interaction.followup.send(message, ephemeral=ephemeral)
        except Exception as e:
            print(f"メッセージ送信中にエラー発生: {e}")

    role_id = 1330626245188386886  # 付与するロールのID
    role = interaction.guild.get_role(role_id)
    if not role:
        print(f"ロールが見つかりませんでした: role_id={role_id}")
        await send_message(interaction, "指定されたロールが見つかりませんでした。")
        return

    try:
        await interaction.user.add_roles(role)
        message = f"アンケート回答ありがとうございます！\nこれにて実験は終了です。\nお疲れ様でした。\n\n**{interaction.user.name}さん**の\n{response_summary}"
        await send_message(interaction, message)
    except discord.Forbidden:
        print(f"権限不足: Botにロール付与権限がありません。user={interaction.user.id}, role={role.id}")
        await send_message(interaction, "エラーが発生しました。BOTの権限を確認してください。")
        return

    developer = bot.get_user(DEVELOPER_ID)
    if developer:
        try:
            await developer.send(f"**{interaction.user.name}さん**の\n{response_summary}")
        except Exception as e:
            print(f"開発者への通知中にエラー発生: {e}")




@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        init_db()
        print("Database initialized")
        print("Bot is ready!")
        await bot.change_presence(activity=discord.CustomActivity(name="実験よろしくね！"))
    except Exception as e:
        print(e)

bot.run(TOKEN)