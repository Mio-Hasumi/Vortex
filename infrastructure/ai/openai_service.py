"""
OpenAI Service for GPT-4o Audio Preview
Unified voice and text processing using latest GPT-4o audio capabilities
"""

import base64
import logging
import openai
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import json
import asyncio
import io

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        Initialize OpenAI service with GPT-4o Audio support
        
        Args:
            api_key: OpenAI API key
            base_url: Optional custom base URL for OpenAI API
        """
        if base_url:
            self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = openai.OpenAI(api_key=api_key)
        self.api_key = api_key
        logger.info("🎵 OpenAI Service initialized with GPT-4o Audio Preview support")

    async def process_voice_input_for_matching(
        self, 
        audio_data: Union[bytes, str],
        audio_format: str = "wav",
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Use GPT-4o Audio to directly process user voice input, extract topics and generate hashtags
        
        New workflow: Audio → GPT-4o Audio → Understand content + Generate hashtags + Audio response
        Replaces: Audio → STT → GPT → Hashtags + TTS
        
        Args:
            audio_data: Audio data (bytes or base64 string)
            audio_format: Audio format (wav, mp3, etc.)
            language: Language preference
            
        Returns:
            {
                "understood_text": "Content spoken by the user",
                "extracted_topics": ["AI", "Entrepreneurship"],  
                "generated_hashtags": ["#AI", "#Entrepreneurship", "#Tech"],
                "match_intent": "Wants to find someone to talk about AI and entrepreneurship",
                "audio_response": "Base64 encoded AI response audio",
                "text_response": "Okay, I understand you want to talk about AI and entrepreneurship, matching you now..."
            }
        """
        try:
            logger.info("🎙️ Processing voice input with GPT-4o Audio for matching...")
            
            # Convert audio to base64 if needed
            if isinstance(audio_data, bytes):
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            else:
                audio_base64 = audio_data
            
            # Use GPT-4o Audio Preview for unified processing
            response = self.client.chat.completions.create(
                model="gpt-4o-audio-preview",
                modalities=["text", "audio"],
                audio={"voice": "alloy", "format": "wav"},
                messages=[
                    {
                        "role": "system", 
                        "content": f"""You are an intelligent voice matching assistant. Users will tell you what topics they want to discuss, please:

1. Understand the user's voice content
2. Extract main topics (in English)
3. Generate English hashtags (for matching algorithm)
4. Respond in {language} to confirm understanding and start matching

Please return in JSON format:
{{
    "understood_text": "Specific content spoken by the user",
    "extracted_topics": ["Topic1", "Topic2"],
    "generated_hashtags": ["#hashtag1", "#hashtag2"],
    "match_intent": "Summary of user's matching intent"
}}

Also respond with a friendly voice to confirm understanding and inform that matching is in progress."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_base64,
                                    "format": audio_format
                                }
                            }
                        ]
                    }
                ]
            )
            
            # Extract response
            message = response.choices[0].message
            
            # Parse JSON response from text
            result_data = {}
            if message.content:
                try:
                    result_data = json.loads(message.content)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response, extracting manually")
                    result_data = {
                        "understood_text": message.content,
                        "extracted_topics": ["General topic"],
                        "generated_hashtags": ["#general"],
                        "match_intent": "Wants to chat"
                    }
            
            # Add audio response
            result_data.update({
                "audio_response": message.audio.data if message.audio else None,
                "text_response": message.content,
                "audio_transcript": message.audio.transcript if message.audio else None,
                "processing_time": datetime.utcnow().isoformat()
            })
            
            logger.info(f"✅ Voice matching processed: {result_data.get('extracted_topics', [])}")
            return result_data
            
        except Exception as e:
            logger.error(f"❌ Voice input processing failed: {e}")
            return {
                "understood_text": "Sorry, I didn't understand what you said",
                "extracted_topics": ["General topic"],
                "generated_hashtags": ["#general"],
                "match_intent": "General chat",
                "audio_response": None,
                "text_response": f"Error processing voice input: {str(e)}",
                "error": str(e)
            }

    async def moderate_room_conversation(
        self,
        audio_data: Optional[Union[bytes, str]] = None,
        text_input: Optional[str] = None,
        conversation_context: List[Dict[str, Any]] = None,
        room_participants: List[str] = None,
        moderation_mode: str = "active_host"
    ) -> Dict[str, Any]:
        """
        使用GPT-4o Audio作为房间AI主持人和秘书
        
        功能：
        - 实时语音对话
        - Fact check
        - 话题建议
        - 气氛调节
        - 内容审核
        
        Args:
            audio_data: 用户语音（如果有）
            text_input: 文字输入（如果有）
            conversation_context: 对话上下文
            room_participants: 房间参与者
            moderation_mode: 主持模式 (active_host, secretary, fact_checker)
            
        Returns:
            AI主持人的回复（音频+文字+建议）
        """
        try:
            logger.info(f"🎭 AI moderating room conversation in {moderation_mode} mode...")
            
            # Build conversation context
            context_messages = [
                {
                    "role": "system",
                    "content": f"""You are an intelligent room host and chat secretary. Current mode: {moderation_mode}

Your responsibilities:
1.  Engage the conversation: Actively provide topics when the conversation is cold
2.  Fact Check: When participants mention potentially inaccurate information, provide friendly verification
3.  Comment: Respond appropriately to conversation content and provide suggestions
4.  Content Moderation: Ensure the conversation is friendly and harmonious
5.  Assistive Guidance: Help participants communicate better

Current room participants: {', '.join(room_participants or [])}

Please provide an appropriate response based on the input content, which can be a voice response, a text suggestion, or a topic recommendation.
The response should be natural, friendly, and helpful."""
                }
            ]
            
            # Add conversation history
            if conversation_context:
                context_messages.extend(conversation_context[-10:])  # Last 10 messages
            
            # Build user message
            user_content = []
            if audio_data:
                if isinstance(audio_data, bytes):
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                else:
                    audio_base64 = audio_data
                    
                user_content.append({
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_base64,
                        "format": "wav"
                    }
                })
            
            if text_input:
                user_content.append({
                    "type": "input_text",
                    "text": text_input
                })
            
            context_messages.append({
                "role": "user",
                "content": user_content if user_content else [{"type": "input_text", "text": "Please assist in moderating the conversation"}]
            })
            
            # Generate AI moderator response
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-audio-preview",
                modalities=["text", "audio"],
                audio={"voice": "nova", "format": "wav"},  # 使用更活泼的声音
                messages=context_messages,
                max_tokens=300
            )
            
            message = response.choices[0].message
            
            return {
                "ai_response": {
                    "text": message.content,
                    "audio": message.audio.data if message.audio else None,
                    "audio_transcript": message.audio.transcript if message.audio else None
                },
                "moderation_type": moderation_mode,
                "suggestions": self._extract_suggestions(message.content or ""),
                "timestamp": datetime.utcnow().isoformat(),
                "participants": room_participants
            }
            
        except Exception as e:
            logger.error(f"❌ Room moderation failed: {e}")
            return {
                "ai_response": {
                    "text": f"AI host encountered an issue: {str(e)}",
                    "audio": None
                },
                "error": str(e)
            }

    def _extract_suggestions(self, ai_text: str) -> List[str]:
        """从AI回复中提取建议"""
        suggestions = []
        if "建议" in ai_text:
            suggestions.append("💡 AI provided a suggestion")
        if "话题" in ai_text:
            suggestions.append("🎯 New topic recommendation")
        if "事实" in ai_text or "信息" in ai_text:
            suggestions.append("🔍 Fact checking")
        return suggestions
    
    def health_check(self) -> Dict[str, Any]:
        """
        检查OpenAI服务健康状态
        
        Returns:
            健康状态信息
        """
        try:
            # 改为使用传统的TTS API来测试连接，避免GPT-4o Audio的复杂参数
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Health check test"
            )
            
            return {
                "status": "healthy",
                "service": "openai_tts",
                "model": "tts-1",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ OpenAI health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "openai_gpt4o_audio",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def text_to_speech(self, text: str, voice: str = "alloy", speed: float = 1.0) -> bytes:
        """
        使用OpenAI TTS API生成语音
        
        Args:
            text: 要转换的文本
            voice: 语音类型
            speed: 语音速度
            
        Returns:
            音频数据（bytes）
        """
        try:
            logger.info(f"🔊 Generating TTS: {text[:50]}...")
            
            # 使用传统的TTS API，更稳定可靠
            response = await asyncio.to_thread(
                lambda: self.client.audio.speech.create(
                    model="tts-1-hd",  # 高质量TTS
                    voice=voice,
                    input=text,
                    speed=speed
                )
            )
            
            # 直接返回音频字节数据
            audio_bytes = response.content
            logger.info("✅ TTS generated successfully")
            return audio_bytes
                
        except Exception as e:
            logger.error(f"❌ TTS generation failed: {e}")
            raise

    async def extract_topics_and_hashtags(
        self, 
        text: str, 
        context: Dict[str, Any] = None,
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Extract topics and generate hashtags from text using GPT-4
        
        Args:
            text: Input text to analyze
            context: Additional context (user info, preferences, etc.)
            language: Language preference
            
        Returns:
            Dictionary with extracted topics, hashtags, category, sentiment, etc.
        """
        try:
            logger.info(f"🧠 Extracting topics from text: {text[:100]}...")
            
            # Build context prompt
            context_info = ""
            if context:
                context_info = f"\nUser context: {json.dumps(context, indent=2)}"
            
            # Use GPT-4 for topic extraction
            response = await asyncio.to_thread(
                lambda: self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are an expert at analyzing conversation topics and generating relevant hashtags for social matching.

Your task is to analyze the user's input and extract:
1. Main topics (3-5 specific topics)
2. Relevant hashtags (5-8 hashtags for matching)
3. Category classification
4. Sentiment analysis
5. Conversation style preference

Please respond in JSON format:
{{
    "main_topics": ["Topic1", "Topic2", "Topic3"],
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
    "category": "technology|business|lifestyle|entertainment|education|sports|health|travel|other",
    "sentiment": "positive|negative|neutral",
    "conversation_style": "casual|professional|academic|creative",
    "confidence": 0.95,
    "summary": "Brief summary of what the user wants to discuss"
}}

Language preference: {language}
Focus on creating hashtags that will help match users with similar interests.{context_info}"""
                        },
                        {
                            "role": "user",
                            "content": f"Please analyze this text and extract topics/hashtags: {text}"
                        }
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            try:
                result = json.loads(content)
                logger.info(f"✅ Topics extracted: {result.get('main_topics', [])}")
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, creating fallback")
                # Fallback parsing
                return {
                    "main_topics": ["general", "conversation"],
                    "hashtags": ["#chat", "#social", "#conversation"],
                    "category": "other", 
                    "sentiment": "neutral",
                    "conversation_style": "casual",
                    "confidence": 0.5,
                    "summary": "General conversation topic",
                    "raw_response": content
                }
                
        except Exception as e:
            logger.error(f"❌ Topic extraction failed: {e}")
            # Return fallback data
            return {
                "main_topics": ["general"],
                "hashtags": ["#general", "#chat"],
                "category": "other",
                "sentiment": "neutral", 
                "conversation_style": "casual",
                "confidence": 0.1,
                "summary": "Could not analyze topics",
                "error": str(e)
            }