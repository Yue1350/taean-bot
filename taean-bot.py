# --- 커스텀 이모지 처리 부분 ---
    custom_emojis = re.findall(r"<(a?):(\w+):(\d+)>", message.content)
    if custom_emojis:
        try:
            # 원본 메시지 삭제
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            # 1. 메시지 본문에서 이모지 태그(<:name:id>)를 제거하고 pure한 텍스트만 남김
            cleaned_content = re.sub(r"<(a?):(\w+):(\d+)>", "", message.content).strip()

            # 2. 첫 번째 이모지 URL 생성
            is_animated, emoji_name, emoji_id = custom_emojis[0]
            ext = "gif" if is_animated else "png"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=1024"

            # 3. 이모티콘을 크게 띄워줄 임베드 생성
            embed = discord.Embed(color=discord.Color.blurple())
            embed.set_image(url=emoji_url)

            # 4. 웹훅 전송 (텍스트가 있으면 content로 추가, 이모티콘은 큰 이미지로 전송)
            webhook = await message.channel.create_webhook(name="EmojiTransmitter")
            await webhook.send(
                content=cleaned_content if cleaned_content else None,
                embed=embed,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            )
            await webhook.delete()

            # 5. TTS 읽기 처리 (텍스트가 같이 있으면 텍스트만 읽고, 이모지만 있으면 '이모지를 보냈습니다' 출력)
            if message.channel.id == target_channel_id:
                voice_client = message.guild.voice_client
                if voice_client and (message.author.voice and message.author.voice.channel == voice_client.channel or guild_settings.get('read_non_vc')):
                    if cleaned_content:
                        tts_text = cleaned_content
                        tts_text = auto_roman_to_korean(tts_text)
                        tts_text = convert_numbers_to_korean(tts_text)
                    else:
                        tts_text = f"{author_name}님이 이모지를 보냈습니다."

                    filename = f"tts_emoji_{message.id}.wav"

                    try:
                        audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, user_settings)
                        with open(filename, "wb") as out:
                            out.write(audio_content)

                        while voice_client.is_playing():
                            await asyncio.sleep(0.3)

                        await play_tts(voice_client, filename)
                    except Exception as e:
                        print(f"❌ 이모지 TTS 생성 실패 원인: {e}")
            return
        except Exception as e:
            print(f"❌ 이모지 전송 실패: {e}")
