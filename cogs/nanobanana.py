import io
import streamlit as st
from google import genai
from google.genai import types

# 페이지 기본 설정
st.set_page_config(page_title="나노 바나나 이미지 생성 봇", page_icon="🍌")
st.title("🍌 나노 바나나 이미지 생성 봇")

# 사이드바에서 Gemini API 키 입력 받기
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")

# 프롬프트 입력 창
prompt = st.text_area("어떤 이미지를 만들고 싶어?", placeholder="예: 바나나 옷을 입은 귀여운 고양이, 픽사 스타일")

# 이미지 비율 및 수량 옵션
col1, col2 = st.columns(2)
with col1:
    aspect_ratio = st.selectbox("이미지 비율", ["1:1", "3:4", "4:3", "9:16", "16:9"])
with col2:
    output_format = st.selectbox("파일 형식", ["image/jpeg", "image/png"])

# 이미지 생성 버튼
if st.button("이미지 생성하기 🚀"):
    if not api_key:
        st.error("API 키를 먼저 입력해 줘!")
    elif not prompt:
        st.warning("프롬프트를 입력해 줘!")
    else:
        with st.spinner("멋진 이미지를 만들고 있어, 잠시만 기다려 줘..."):
            try:
                # Gemini SDK 클라이언트 설정
                client = genai.Client(api_key=api_key)

                # Imagen 모델 호출
                response = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type=output_format,
                        aspect_ratio=aspect_ratio
                    )
                )

                # 결과 출력
                for generated_image in response.generated_images:
                    image_bytes = generated_image.image.image_bytes
                    st.image(image_bytes, caption=f"결과물: {prompt}", use_container_width=True)
                    
                    # 다운로드 버튼 제공
                    st.download_button(
                        label="이미지 다운로드 📥",
                        data=image_bytes,
                        file_name="nano_banana_image.png" if output_format == "image/png" else "nano_banana_image.jpg",
                        mime=output_format
                    )
            except Exception as e:
                st.error(f"이미지 생성 실패: {e}")
