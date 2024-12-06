import streamlit as st
import json
import os
import re
from dotenv import load_dotenv
from systemprompt import SystemPrompt
from anthropic import AnthropicVertex
from google.cloud import texttospeech
import base64
import html

load_dotenv()
system_prompt = SystemPrompt.getSystemPrompt()

client = AnthropicVertex(project_id="gen-ai-demo-433513", region="us-east5")
tts_client = texttospeech.TextToSpeechClient()

st.title("💬 Firefly AI")

def generate_thai_speech(text):
    """Generate Thai speech from text using Google Cloud TTS"""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    # Configure voice parameters for Thai
    voice = texttospeech.VoiceSelectionParams(
        language_code="th-TH",
        name="th-TH-Standard-A",  # You can change to other Thai voices if needed
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    
    # Configure audio parameters
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    # Generate speech
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    # Convert audio content to base64 for HTML audio player
    audio_content = base64.b64encode(response.audio_content).decode('utf-8')
    audio_html = f'<audio controls><source src="data:audio/mp3;base64,{audio_content}" type="audio/mp3"></audio>'
    
    return audio_html

def get_next_available_id(chats):
    """หา ID ที่ว่างอยู่ถัดไป"""
    if not chats:
        return 1
    existing_ids = set(chat['id'] for chat in chats)
    for i in range(1, max(existing_ids) + 2):
        if i not in existing_ids:
            return i
    return len(chats) + 1

def separate_response(text):
    emotion_match = re.search(r'<Emotion>(.*?)<\/Emotion>', text)
    if emotion_match:
        emotion = emotion_match.group(1)
        message = text.replace(emotion_match.group(0), '').strip()
    else:
        emotion = None
        message = text
    return emotion, message

def save_chat_history(charts, filename="all_chats.json"):
    with open(filename, 'w') as f:
        json.dump(charts, f)

def load_all_chats(filename="all_chats.json"):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump([], f)
    with open(filename, 'r') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

def get_response(user_prompt, message_list):
    message_list.append({"role": "user", "content": user_prompt})
    response = client.messages.create(
        model="claude-3-5-sonnet@20240620",
        max_tokens=1500,
        system=system_prompt,
        messages=message_list,
    )
    return response.content[0].text

def display_sticker(emotion):
    sticker_map = {
        "Normal": "./image/Sticker_PPG_15_Firefly_03.jpg",
        "Happy": "./image/Sticker_PPG_15_Firefly_01.jpg",
        "Confused": "./image/Sticker_PPG_15_Firefly_02.jpg",
        "Angry": "./image/Sticker_PPG_15_Firefly_04.jpg",
        "Sad": "./image/Firefly5.jpg",
    }
    sticker_path = sticker_map.get(emotion)
    if sticker_path and os.path.exists(sticker_path):
        st.image(sticker_path, width=100)

def display_chat_messages(messages):
    for message in messages:
        role = "user" if message["role"] == "user" else "assistant"
        avatar = "🧑" if role == "user" else "./image/Firefly4.jpg"
        with st.chat_message(role, avatar=avatar):
            emotion, content = separate_response(message["content"])
            st.write(content)
            
            # Generate and display speech for assistant messages
            if role == "assistant":
                if emotion:
                    display_sticker(emotion)
                # Generate Thai speech from the content
                audio_html = generate_thai_speech(content)
                # Display audio player
                st.markdown(audio_html, unsafe_allow_html=True)

all_chats = load_all_chats()


if "active_chat" not in st.session_state:
    # สร้างแชทใหม่
    new_chat = {
        "id": get_next_available_id(all_chats),
        "messages": []
    }
    st.session_state["active_chat"] = new_chat
    
    # บันทึกแชทใหม่ลงใน all_chats
    all_chats.append(new_chat)
    save_chat_history(all_chats)

# โหลดประวัติแชททั้งหมดเข้า session_state
if "all_chats" not in st.session_state:
    st.session_state["all_chats"] = all_chats

# ตั้งค่าเริ่มต้นสำหรับแชทที่เลือก
if "selected_chat_id" not in st.session_state:
    st.session_state["selected_chat_id"] = st.session_state["active_chat"]["id"]
# Sidebar for chat management

st.sidebar.title("Chat History")
new_chat_button = st.sidebar.button("➕ New Chat")

if new_chat_button:
    if st.session_state["active_chat"]["messages"]:  # Save current chat if it has messages
        st.session_state["all_chats"].append(st.session_state["active_chat"])
    st.session_state["active_chat"] = {
        "id": get_next_available_id(st.session_state["all_chats"]),
        "messages": [],
    }
    st.session_state["selected_chat_id"] = None
    save_chat_history(st.session_state["all_chats"])

# Rest of your existing code remains the same...
sorted_chats = sorted(st.session_state["all_chats"], key=lambda x: x['id'])
for chat in sorted_chats:
    with st.sidebar.expander(f"Chat #{chat['id']}"):
        if st.button(f"Show Chat #{chat['id']}", key=f"show_{chat['id']}"):
            st.session_state["selected_chat_id"] = chat['id']
    
        if st.button(f"❌ Delete Chat #{chat['id']}", key=f"delete_{chat['id']}"):
            # Remove chat from all_chats
            st.session_state["all_chats"] = [c for c in st.session_state["all_chats"] if c['id'] != chat['id']]
            save_chat_history(st.session_state["all_chats"])
            if st.session_state["selected_chat_id"] == chat['id']:
                st.session_state["selected_chat_id"] = None
            st.rerun()

# Update the chat display sections to include audio
if st.session_state["selected_chat_id"] is not None:
    selected_chat = next(
        (chat for chat in st.session_state["all_chats"] 
         if chat["id"] == st.session_state["selected_chat_id"]), 
        None
    )
    if selected_chat:
        st.subheader(f"Chat History #{selected_chat['id']}")
        display_chat_messages(selected_chat["messages"])
        
        user_input = st.chat_input("Continue this conversation...")
        if user_input:
            with st.chat_message("user", avatar="🧑"):
                st.write(user_input)

            response = get_response(
                user_input, 
                selected_chat["messages"]
            )
            emotion, content = separate_response(response)
            selected_chat["messages"].append(
                {"role": "assistant", "content": response}
            )
            
            with st.chat_message("assistant", avatar="./image/Firefly4.jpg"):
                st.write(content)
                if emotion:
                    display_sticker(emotion)
                # Generate and display Thai speech
                audio_html = generate_thai_speech(content)
                st.markdown(audio_html, unsafe_allow_html=True)

            for i, chat in enumerate(st.session_state["all_chats"]):
                if chat["id"] == selected_chat["id"]:
                    st.session_state["all_chats"][i] = selected_chat
                    break
            
            save_chat_history(st.session_state["all_chats"])
            st.rerun()

else:
    display_chat_messages(st.session_state["active_chat"]["messages"])
    
    user_input = st.chat_input("Say something...")
    if user_input:
        with st.chat_message("user", avatar="🧑"):
            st.write(user_input)

        response = get_response(
            user_input, 
            st.session_state["active_chat"]["messages"]
        )
        emotion, content = separate_response(response)
        st.session_state["active_chat"]["messages"].append(
            {"role": "assistant", "content": response}
        )
        
        with st.chat_message("assistant", avatar="./image/Firefly4.jpg"):
            st.write(content)
            if emotion:
                display_sticker(emotion)
            # Generate and display Thai speech
            audio_html = generate_thai_speech(content)
            st.markdown(audio_html, unsafe_allow_html=True)

        save_chat_history(st.session_state["all_chats"])
        st.rerun()