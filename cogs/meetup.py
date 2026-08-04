import re, asyncio, discord
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands

def parse_datetime(date_str: str = None, time_str: str = None) -> datetime:
    now = datetime.now()
    year, month, day = now.year, now.month, now.day
    
    if date_str:
        date_pattern = r'(?:(\d{4})[-년\.]\s*)?(\d{1,2})[-월\.]\s*(\d{1,2})'
        match_date = re.search(date_pattern, date_str)
        if match_date:
            y, m, d = match_date.groups()
            year = int(y) if y else now.year
            month, day = int(m), int(d)
        else:
            return None

    hour, minute = 9, 0
    if time_str:
        time_pattern = r'(?:(오전|오후)\s*)?(\d{1,2})(?:[:시]\s*(\d{1,2}))?'
        match_time = re.search(time_pattern, time_str)
        if match_time:
            ampm, h, min_val = match_time.groups()
            h = int(h)
            min_val = int(min_val) if min_val else 0
            
            if ampm == "오후" and h < 12:
                h += 12
            elif ampm == "오전" and h == 12:
                h = 0
            
            hour, minute = h, min_val

    try:
        target_dt = datetime(year, month, day, hour, minute)
        if date_str and target_dt < now and not match_date.group(1):
            target_dt = target_dt.replace(year=year + 1)
        return target_dt
    except ValueError:
        return None

class MeetupView(discord.ui.View):
    def __init__(self, author: discord.Member, content: str, meetup_dt: datetime, bot: commands.Bot):
        super().__init__(timeout=None)
        self.author = author
        self.content = content
        self.meetup_dt = meetup_dt
        self.bot = bot
        self.attending = set()
        self.absent = set()

    def update_embed(self) -> discord.Embed:
        dt_str = self.meetup_dt.strftime("%Y년 %m월 %d일 %H시 %M분") if self.meetup_dt else "일시 미정"
        embed = discord.Embed(
            title="📅 정모 참석 여부 투표",
            description=f"**[정모 일시]**\n{dt_str}\n\n**[정모 내용]**\n{self.content}",
            color=discord.Color.blue()
        )
        
        attending_list = "\n".join([f"<@{uid}>" for uid in self.attending]) if self.attending else "없음"
        absent_list = "\n".join([f"<@{uid}>" for uid in self.absent]) if self.absent else "없음"

        embed.add_field(name=f"⭕ 참석 ({len(self.attending)}명)", value=attending_list, inline=True)
        embed.add_field(name=f"❌ 불참 ({len(self.absent)}명)", value=absent_list, inline=True)
        embed.set_footer(text=f"주최자: {self.author.display_name}")
        return embed

    @discord.ui.button(label="참석", style=discord.ButtonStyle.success, custom_id="meetup_attend")
    async def attend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        self.absent.discard(user_id)
        self.attending.add(user_id)
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="불참", style=discord.ButtonStyle.danger, custom_id="meetup_absent")
    async def absent_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        self.attending.discard(user_id)
        self.absent.add(user_id)
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary, custom_id="meetup_edit", emoji="✏️")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("⚠️ 주최자만 정모 내용을 수정할 수 있습니다.", ephemeral=True)
            return

        await interaction.response.send_message("✏️ 정모 내용을 새로 입력해주세요.", ephemeral=True)

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            new_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            try:
                await new_msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            self.content = new_msg.content
            await interaction.message.edit(embed=self.update_embed(), view=self)
        except asyncio.TimeoutError:
            await interaction.followup.send("⚠️ 입력 시간이 초과되어 수정이 취소되었습니다.", ephemeral=True)

    @discord.ui.button(label="투표 마감", style=discord.ButtonStyle.secondary, custom_id="meetup_close", emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.author.id:
            for child in self.children:
                child.disabled = True
            
            embed = self.update_embed()
            embed.title = "🔒 [마감] 정모 참석 여부 투표"
            embed.color = discord.Color.dark_grey()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("⚠️ 주최자만 투표를 마감할 수 있습니다.", ephemeral=True)

class MeetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def schedule_reminder(self, channel: discord.TextChannel, meetup_dt: datetime, view: MeetupView):
        now = datetime.now()
        delay = (meetup_dt - now).total_seconds()

        if delay > 0:
            await asyncio.sleep(delay)

            if view.attending:
                mentions = " ".join([f"<@{uid}>" for uid in view.attending])
            else:
                mentions = "@everyone"

            dt_str = meetup_dt.strftime("%Y년 %m월 %d일 %H시 %M분")
            embed = discord.Embed(
                title="🔔 [정모 알림] 오늘 정모가 예정되어 있습니다.",
                description=f"**[정모 일시]** {dt_str}\n**[내용]** {view.content}",
                color=discord.Color.gold()
            )
            await channel.send(content=f"📢 정모 알림! {mentions}", embed=embed)

    @app_commands.command(name="정모", description="정모 공지를 작성하고 참석/불참 투표를 진행합니다.")
    @app_commands.describe(
        내용="정모 장소 및 상세 내용",
        날짜="정모 날짜 (선택 사항, 예: 3/5, 3월 5일)",
        시간="정모 시간 (선택 사항, 예: 19시, 오후 7시)"
    )
    async def create_meetup(self, interaction: discord.Interaction, 내용: str, 날짜: str = None, 시간: str = None):
        meetup_dt = parse_datetime(날짜, 시간)

        if 날짜 and not meetup_dt:
            await interaction.response.send_message("⚠️ 날짜 형식을 인식하지 못했습니다. (예: 3/5, 3월 5일)", ephemeral=True)
            return

        view = MeetupView(author=interaction.user, content=내용, meetup_dt=meetup_dt, bot=self.bot)
        embed = view.update_embed()

        await interaction.response.send_message("✅ 정모 공지 투표가 생성되었습니다!", ephemeral=True)
        msg = await interaction.channel.send(content="@everyone", embed=embed, view=view)

        try:
            await msg.pin(reason="정모 공지 자동 고정")
            await asyncio.sleep(0.5)
            async for sys_msg in interaction.channel.history(limit=5):
                if sys_msg.type == discord.MessageType.pins_add:
                    await sys_msg.delete()
                    break
        except discord.Forbidden:
            await interaction.followup.send("⚠️ **메시지 고정** 권한이 없어 고정하지 못했습니다.", ephemeral=True)

        if meetup_dt:
            asyncio.create_task(self.schedule_reminder(interaction.channel, meetup_dt, view))

async def setup(bot: commands.Bot):
    await bot.add_cog(MeetupCog(bot))
