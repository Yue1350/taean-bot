import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# 1. 정모 투표 View 클래스
class MeetupView(discord.ui.View):
    def __init__(self, author: discord.Member, content: str, bot: discord.Client):
        super().__init__(timeout=None)
        self.author = author
        self.content = content
        self.bot = bot
        self.attending = set()
        self.absent = set()

    def update_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📅 정모 참석 여부 투표",
            description=f"**[정모 내용]**\n{self.content}",
            color=discord.Color.blue()
        )
        
        attending_list = "\n".join([f"<@{uid}>" for uid in self.attending]) if self.attending else "없음"
        absent_list = "\n".join([f"<@{uid}>" for uid in self.absent]) if self.absent else "없음"

        embed.add_field(name=f"⭕ 참석 ({len(self.attending)}명)", value=attending_list, inline=True)
        embed.add_field(name=f"❌ 불참 ({len(self.absent)}명)", value=absent_list, inline=True)
        embed.set_footer(text=f"주최자: {self.author.display_name}")
        return embed

    @discord.ui.button(label="참석", style=discord.ButtonStyle.success, custom_id="meetup_attend", emoji="⭕")
    async def attend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        self.absent.discard(user_id)
        self.attending.add(user_id)
        
        embed = self.update_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="불참", style=discord.ButtonStyle.danger, custom_id="meetup_absent", emoji="❌")
    async def absent_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        self.attending.discard(user_id)
        self.absent.add(user_id)
        
        embed = self.update_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary, custom_id="meetup_edit", emoji="✏️")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ 주최자만 정모 내용을 수정할 수 있어!", ephemeral=True)
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
            embed = self.update_embed()
            await interaction.message.edit(embed=embed, view=self)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ 입력 시간이 초과되어 수정이 취소되었어.", ephemeral=True)

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
            await interaction.response.send_message("❌ 주최자만 투표를 마감할 수 있어.", ephemeral=True)


# 2. 정모 Cog 클래스
class MeetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 명령어: /정모
    @app_commands.command(name="정모", description="정모 공지를 작성하고 참석/불참 투표를 진행합니다.")
    @app_commands.describe(info="정모 일시, 장소, 내용 등을 작성해주세요.")
    async def create_meetup(self, interaction: discord.Interaction, info: str):
        view = MeetupView(author=interaction.user, content=info, bot=self.bot)
        embed = view.update_embed()

        await interaction.response.send_message("📌 정모 공지 투표가 생성되었습니다!", ephemeral=True)

        msg = await interaction.channel.send(content="@everyone", embed=embed, view=view)

        try:
            await msg.pin(reason="정모 공지 자동 고정")
            
            await asyncio.sleep(0.5)
            async for sys_msg in interaction.channel.history(limit=5):
                if sys_msg.type == discord.MessageType.pins_add:
                    await sys_msg.delete()
                    break
        except discord.Forbidden:
            await interaction.followup.send("⚠️ 봇에게 '메시지 고정 및 관리' 권한이 없어 고정 메시지를 처리하지 못했습니다.", ephemeral=True)
        except Exception as e:
            print(f"❌ 메시지 고정/시스템 메시지 삭제 실패: {e}")

async def setup(bot):
    await bot.add_cog(MeetupCog(bot))
