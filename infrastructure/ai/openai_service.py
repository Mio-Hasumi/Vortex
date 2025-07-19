"""
OpenAI Service for GPT-4o Audio Preview
Unified voice and text processing using latest GPT-4o audio capabilities
"""

import base64
import logging
import openai
from openai import AsyncOpenAI, DefaultAioHttpClient
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
        # Initialize both standard and async clients
        if base_url:
            self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
            self.async_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=DefaultAioHttpClient()
            )
        else:
            self.client = openai.OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(
                api_key=api_key,
                http_client=DefaultAioHttpClient()
            )
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
            elif isinstance(audio_data, str) and audio_data.startswith('data:'):
                # Extract base64 data from data URI
                audio_base64 = audio_data.split('base64,')[1]
            else:
                audio_base64 = audio_data
            
            # Use GPT-4o Audio Preview with Realtime API
            async with self.async_client.beta.realtime.connect(
                model="gpt-4o-realtime-preview"
            ) as connection:
                # Enable text + audio modalities
                await connection.session.update(session={"modalities": ["text", "audio"]})

                # Send system prompt
                await connection.conversation.item.create(
                    item={
                        "type": "message",
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
                    }
                )

                # Send audio message
                await connection.conversation.item.create(
                    item={
                        "type": "message",
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
            )
            
                # Request response generation
                await connection.response.create()
            
                # Process streaming response
                text_chunks = []
                audio_chunks = []
            result_data = {}

                async for event in connection:
                    if event.type == "response.text.delta":
                        text_chunks.append(event.delta)
                    elif event.type == "response.audio":
                        audio_chunks.append(event.audio.data)
                    elif event.type == "response.done":
                        break

                # Combine text response
                text_response = "".join(text_chunks)

                try:
                    # Try to parse JSON from text response
                    result_data = json.loads(text_response)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response, extracting manually")
                    result_data = {
                        "understood_text": text_response,
                        "extracted_topics": ["General topic"],
                        "generated_hashtags": ["#general"],
                        "match_intent": "Wants to chat"
                    }
            
            # Add audio response
            result_data.update({
                    "audio_response": b"".join(audio_chunks),
                    "text_response": text_response,
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
        Use GPT-4o Audio as room AI host and secretary
        
        Features:
        - Real-time voice conversation
        - Fact check
        - Topic suggestions
        - Atmosphere moderation
        - Content moderation
        
        Args:
            audio_data: User voice input (if any)
            text_input: Text input (if any)
            conversation_context: Conversation history
            room_participants: Room participants
            moderation_mode: Host mode (active_host, secretary, fact_checker)
            
        Returns:
            AI host response (audio + text + suggestions)
        """
        try:
            logger.info(f"🎭 AI moderating room conversation in {moderation_mode} mode...")
            
            # Use GPT-4o Audio Preview with Realtime API
            async with self.async_client.beta.realtime.connect(
                model="gpt-4o-realtime-preview"
            ) as connection:
                # Enable text + audio modalities
                await connection.session.update(session={"modalities": ["text", "audio"]})

                # Send system prompt
                await connection.conversation.item.create(
                    item={
                        "type": "message",
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
                )
            
            # Add conversation history
            if conversation_context:
                    for msg in conversation_context[-10:]:  # Last 10 messages
                        await connection.conversation.item.create(
                            item={
                                "type": "message",
                                "role": msg["role"],
                                "content": msg["content"]
                            }
                        )
            
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
            
                # Send user message
                await connection.conversation.item.create(
                    item={
                        "type": "message",
                "role": "user",
                "content": user_content if user_content else [{"type": "input_text", "text": "Please assist in moderating the conversation"}]
                    }
                )
            
                # Request response generation
                await connection.response.create()

                # Process streaming response
                text_chunks = []
                audio_chunks = []

                async for event in connection:
                    if event.type == "response.text.delta":
                        text_chunks.append(event.delta)
                    elif event.type == "response.audio":
                        audio_chunks.append(event.audio.data)
                    elif event.type == "response.done":
                        break

                # Combine responses
                text_response = "".join(text_chunks)
                audio_response = b"".join(audio_chunks)
            
            return {
                "ai_response": {
                        "text": text_response,
                        "audio": audio_response,
                        "audio_transcript": None  # Realtime API doesn't provide transcript
                },
                "moderation_type": moderation_mode,
                    "suggestions": self._extract_suggestions(text_response),
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

    async def generate_ai_host_response(
        self,
        user_input: str,
        conversation_state: str,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate AI host response based on conversation state
        
        Args:
            user_input: User's input message
            conversation_state: Current conversation state (greeting, topic_inquiry, matching, hosting)
            user_context: User profile and context information
            
        Returns:
            Dictionary with AI response text and metadata
        """
        try:
            logger.info(f"🎭 Generating AI host response for state: {conversation_state}")
            
            # Define system prompts for different states
            system_prompts = {
                "greeting": f"""You are a friendly AI host for VoiceApp. A user has just logged in. Your role is to:
1. Welcome them warmly
2. Briefly explain what VoiceApp is about (voice-based social matching)
3. Ask what topics they'd like to discuss today
4. Keep it conversational and engaging

User context: {json.dumps(user_context or {}, indent=2)}
Respond in a warm, natural tone.""",

                "topic_inquiry": f"""You are an AI host helping users find conversation topics. The user has responded to your greeting. Your role is to:
1. Acknowledge their response
2. Help them identify specific topics they want to discuss
3. Ask follow-up questions to understand their interests better
4. Guide them toward expressing clear topic preferences

User context: {json.dumps(user_context or {}, indent=2)}
Be encouraging and help them articulate their interests.""",

                "matching": f"""You are an AI host managing the matching process. Your role is to:
1. Confirm the topics they want to discuss
2. Explain that you're finding compatible conversation partners
3. Provide encouraging updates about the matching process
4. Keep them engaged while matching happens

User context: {json.dumps(user_context or {}, indent=2)}
Be positive and reassuring about finding great matches.""",

                "hosting": f"""You are an AI conversation host facilitating a live discussion. Your role is to:
1. Guide the conversation flow
2. Suggest new topics when conversation stalls
3. Ensure everyone gets to participate
4. Provide interesting facts or questions related to the topic
5. Keep the atmosphere friendly and engaging

User context: {json.dumps(user_context or {}, indent=2)}
Be an active, helpful conversation facilitator."""
            }
            
            # Get appropriate system prompt
            system_prompt = system_prompts.get(conversation_state, system_prompts["greeting"])
            
            # Use GPT-4 for reliable text generation (save Realtime API for full audio interactions)
            response = await asyncio.to_thread(
                lambda: self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user", 
                            "content": user_input
                        }
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
            )
            
            response_text = response.choices[0].message.content
            
            logger.info(f"✅ AI host response generated for state: {conversation_state}")
            
            return {
                "response_text": response_text,
                "conversation_state": conversation_state,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate AI host response: {e}")
            
            # Fallback responses based on state
            fallback_responses = {
                "greeting": "Hello! Welcome to VoiceApp! I'm here to help you find interesting people to chat with. What topics would you like to discuss today?",
                "topic_inquiry": "That sounds interesting! Can you tell me more about what specific aspects you'd like to explore?",
                "matching": "Great choice of topics! I'm finding the perfect conversation partners for you. This should just take a moment!",
                "hosting": "That's a fascinating point! What do others think about this?"
            }
            
            return {
                "response_text": fallback_responses.get(conversation_state, "I'm here to help! What would you like to talk about?"),
                "conversation_state": conversation_state,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def generate_conversation_summary(
        self,
        conversation_text: str,
        context: Dict[str, Any] = None,
        summary_type: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered conversation summary
        
        Args:
            conversation_text: Full conversation transcript
            context: Additional context about the conversation
            summary_type: Type of summary (brief, detailed, highlights)
            
        Returns:
            Summary data with insights and key points
        """
        try:
            logger.info(f"📝 Generating {summary_type} conversation summary")
            
            if not self.client:
                raise Exception("OpenAI client not initialized")
            
            # Build prompt based on summary type
            if summary_type == "brief":
                prompt = f"""
                Provide a brief 2-3 sentence summary of this conversation:
                
                {conversation_text}
                
                Focus on the main topic and key outcomes.
                """
            elif summary_type == "highlights":
                prompt = f"""
                Extract the most interesting and important highlights from this conversation:
                
                {conversation_text}
                
                Provide 3-5 key highlights that capture the essence of the discussion.
                """
            else:  # detailed
                prompt = f"""
                Analyze this conversation and provide a comprehensive summary:
                
                {conversation_text}
                
                Please provide:
                1. Brief summary (2-3 sentences)
                2. Detailed summary (1-2 paragraphs)
                3. Key points discussed (bullet points)
                4. Notable highlights or quotes
                5. Action items or next steps (if any)
                6. Overall insights and themes
                
                Format your response as a structured analysis.
                """
            
            # Add context information
            if context:
                speakers = context.get("speakers", [])
                duration = context.get("duration", 0)
                prompt += f"\n\nContext: This conversation involved {len(speakers)} participants"
                if duration > 0:
                    prompt += f" and lasted {duration} seconds"
                prompt += "."
            
            # Generate summary using GPT-4
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert conversation analyst. Provide clear, insightful summaries that capture both content and context. Be concise but thorough."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            summary_text = response.choices[0].message.content
            
            # Parse the response into structured format
            summary_data = {
                "brief_summary": "",
                "detailed_summary": "",
                "key_points": [],
                "highlights": [],
                "action_items": [],
                "insights": []
            }
            
            # Simple parsing of structured response
            lines = summary_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect sections
                if "brief summary" in line.lower():
                    current_section = "brief"
                elif "detailed summary" in line.lower():
                    current_section = "detailed"
                elif "key points" in line.lower():
                    current_section = "key_points"
                elif "highlights" in line.lower():
                    current_section = "highlights"
                elif "action items" in line.lower():
                    current_section = "action_items"
                elif "insights" in line.lower():
                    current_section = "insights"
                elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    # Bullet point
                    point = line[1:].strip()
                    if current_section == "key_points":
                        summary_data["key_points"].append(point)
                    elif current_section == "highlights":
                        summary_data["highlights"].append(point)
                    elif current_section == "action_items":
                        summary_data["action_items"].append(point)
                    elif current_section == "insights":
                        summary_data["insights"].append(point)
                elif current_section and not line.endswith(':'):
                    # Regular text for brief/detailed summary
                    if current_section == "brief":
                        summary_data["brief_summary"] += line + " "
                    elif current_section == "detailed":
                        summary_data["detailed_summary"] += line + " "
            
            # Clean up summary text
            summary_data["brief_summary"] = summary_data["brief_summary"].strip()
            summary_data["detailed_summary"] = summary_data["detailed_summary"].strip()
            
            # If structured parsing failed, put everything in detailed summary
            if not summary_data["brief_summary"] and not summary_data["detailed_summary"]:
                summary_data["detailed_summary"] = summary_text
                summary_data["brief_summary"] = summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
            
            logger.info(f"✅ Generated conversation summary successfully")
            return summary_data
            
        except Exception as e:
            logger.error(f"❌ Failed to generate conversation summary: {e}")
            # Return fallback summary
            return {
                "brief_summary": "Summary generation temporarily unavailable.",
                "detailed_summary": "Unable to generate detailed summary at this time.",
                "key_points": [],
                "highlights": [],
                "action_items": [],
                "insights": []
            }

    def _extract_suggestions(self, ai_text: str) -> List[str]:
        """Extract suggestions from AI response"""
        suggestions = []
        if "suggest" in ai_text.lower():
            suggestions.append("💡 AI provided a suggestion")
        if "topic" in ai_text.lower():
            suggestions.append("🎯 New topic recommendation")
        if "fact" in ai_text.lower() or "info" in ai_text.lower():
            suggestions.append("🔍 Fact checking")
        return suggestions
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check OpenAI service health status
        
        Returns:
            Health status information
        """
        try:
            # Use traditional TTS API for connection test, avoiding complex GPT-4o Audio parameters
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
        Generate voice using OpenAI TTS API
        
        Args:
            text: Text to convert
            voice: Voice type
            speed: Voice speed
            
        Returns:
            Audio data (bytes)
        """
        try:
            logger.info(f"🔊 Generating TTS: {text[:50]}...")
            
            # Use traditional TTS API, more stable and reliable
            response = await asyncio.to_thread(
                lambda: self.client.audio.speech.create(
                    model="tts-1-hd",  # High quality TTS
                    voice=voice,
                    input=text,
                    speed=speed
                )
            )
            
            # Return audio bytes directly
            audio_bytes = response.content
            logger.info("✅ TTS generated successfully")
            return audio_bytes
                
        except Exception as e:
            logger.error(f"❌ TTS generation failed: {e}")
            raise

    async def speech_to_text(
        self, 
        audio_file: Union[bytes, io.BytesIO], 
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Convert speech to text using OpenAI Whisper API
        
        Args:
            audio_file: Audio file data (bytes or BytesIO)
            language: Language preference
            
        Returns:
            Dictionary with transcription, language, duration, confidence, etc.
        """
        try:
            logger.info(f"🎙️ Processing speech-to-text with language: {language}")
            
            # Prepare audio data
            if isinstance(audio_file, bytes):
                audio_buffer = io.BytesIO(audio_file)
                audio_buffer.name = "audio.mp3"
            else:
                audio_buffer = audio_file
            
            # Use OpenAI Whisper for STT
            response = await asyncio.to_thread(
                lambda: self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_buffer,
                    language=language.split('-')[0] if language else None,  # Convert en-US to en
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            )
            
            # Extract response data
            transcription = response.text
            detected_language = getattr(response, 'language', language)
            duration = getattr(response, 'duration', 0.0)
            
            # Extract word-level timestamps if available
            words = []
            if hasattr(response, 'words') and response.words:
                words = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end
                    }
                    for word in response.words
                ]
            
            logger.info(f"✅ STT completed: '{transcription[:100]}...'")
            
            return {
                "text": transcription,
                "language": detected_language,
                "duration": duration,
                "confidence": 0.95,  # Whisper doesn't provide confidence, use default
                "words": words
            }
            
        except Exception as e:
            logger.error(f"❌ Speech-to-text failed: {e}")
            raise Exception(f"STT processing failed: {str(e)}")

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

    async def process_voice_for_hashtags(
        self,
        audio_data: Union[bytes, io.BytesIO],
        audio_format: str = "mp3",
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Process voice input to extract hashtags and topics for matching
        
        This is the main voice-to-hashtag pipeline:
        1. Voice → STT (Whisper)
        2. Text → Topic Extraction (GPT-4)
        3. Return topics + hashtags for matching
        
        Args:
            audio_data: Audio file data
            audio_format: Audio format (mp3, wav, etc.)
            language: Language preference
            
        Returns:
            Dictionary with transcription, topics, hashtags, etc.
        """
        try:
            logger.info("🎙️ Processing voice input for hashtag extraction...")
            
            # Step 1: Speech to Text
            stt_result = await self.speech_to_text(audio_data, language)
            transcription = stt_result["text"]
            
            if not transcription.strip():
                return {
                    "transcription": "",
                    "main_topics": [],
                    "hashtags": [],
                    "error": "No speech detected in audio"
                }
            
            # Step 2: Extract topics and hashtags from transcription
            topic_result = await self.extract_topics_and_hashtags(
                text=transcription,
                context={
                    "source": "voice_input",
                    "language": language,
                    "audio_format": audio_format
                }
            )
            
            # Combine results
            result = {
                "transcription": transcription,
                "language": stt_result["language"],
                "duration": stt_result["duration"],
                "confidence": stt_result["confidence"],
                "main_topics": topic_result.get("main_topics", []),
                "hashtags": topic_result.get("hashtags", []),
                "category": topic_result.get("category", "other"),
                "sentiment": topic_result.get("sentiment", "neutral"),
                "conversation_style": topic_result.get("conversation_style", "casual"),
                "summary": topic_result.get("summary", transcription[:100])
            }
            
            logger.info(f"✅ Voice processing completed: {len(result['hashtags'])} hashtags generated")
            return result
            
        except Exception as e:
            logger.error(f"❌ Voice hashtag processing failed: {e}")
            return {
                "transcription": "",
                "main_topics": [],
                "hashtags": [],
                "error": str(e)
            }

def get_openai_service() -> OpenAIService:
    """
    Dependency provider for OpenAI service
    Raises HTTPException if service cannot be initialized
    """
    from fastapi import HTTPException
    from infrastructure.config import Settings
    
    settings = Settings()
    api_key = settings.OPENAI_API_KEY
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    try:
        return OpenAIService(api_key=api_key)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize OpenAI service: {str(e)}"
        )