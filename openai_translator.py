#!/usr/bin/env python
import json
import requests
import time
import re
from typing import Optional, List
import tiktoken

class OpenAITranslator:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-3.5-turbo", max_tokens: int = 2000,
                 temperature: float = 0.3, chunk_size: int = 3000):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.chunk_size = chunk_size  # Maximum tokens per chunk
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback if tiktoken is not available
            self.tokenizer = None
            print("Warning: tiktoken not available, using approximate token counting")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tokenizer or approximate method"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Approximate token counting (roughly 4 characters per token)
            return len(text) // 4

    def split_text_into_chunks(self, text: str, target_language: str, source_language: str = "en") -> List[str]:
        """Split text into chunks that fit within token limits"""
        # Reserve tokens for the prompt template and overhead
        prompt_template = f"""You are a professional academic translator. Your task is to translate the following text from {source_language} to {target_language}.

CRITICAL REQUIREMENTS:
1. Translate EXACTLY what is provided - DO NOT add any content that is not in the original text
2. DO NOT add explanations, examples, or clarifications that are not in the source
3. DO NOT omit any information from the original text
4. Preserve all LaTeX commands, mathematical formulas, and technical notation exactly as they appear
5. Maintain the original structure, formatting, and paragraph breaks
6. Translate ONLY the text content, keeping all non-text elements unchanged
7. If you encounter ambiguous terms, choose the most literal translation rather than adding explanatory context

Text to translate:
{{text}}

Translated text (strictly faithful to original):"""

        template_tokens = self.count_tokens(prompt_template)
        available_tokens = self.chunk_size - template_tokens - 100  # 100 token safety margin

        if available_tokens <= 0:
            print("Warning: Chunk size too small for prompt template")
            available_tokens = 1000

        # If text is small enough, return as single chunk
        if self.count_tokens(text) <= available_tokens:
            return [text]

        chunks = []
        remaining_text = text

        # For LaTeX documents, try to split at logical boundaries
        # First try to split at sections
        section_pattern = r'(\\section\{[^}]+\}\s*)'
        sections = re.split(section_pattern, remaining_text)

        if len(sections) > 1:
            current_chunk = ""
            for i, section in enumerate(sections):
                if i % 2 == 1:  # This is a section header
                    if current_chunk and self.count_tokens(current_chunk + section) > available_tokens:
                        chunks.append(current_chunk.strip())
                        current_chunk = section
                    else:
                        current_chunk += section
                else:  # This is section content
                    if self.count_tokens(current_chunk + section) > available_tokens:
                        # Split this section further
                        sub_chunks = self.split_paragraphs(section, available_tokens)
                        for sub_chunk in sub_chunks:
                            if current_chunk and self.count_tokens(current_chunk + sub_chunk) > available_tokens:
                                chunks.append(current_chunk.strip())
                                current_chunk = sub_chunk
                            else:
                                current_chunk += sub_chunk
                    else:
                        current_chunk += section

            if current_chunk:
                chunks.append(current_chunk.strip())
        else:
            # If no sections, split by paragraphs
            chunks = self.split_paragraphs(text, available_tokens)

        return chunks

    def split_paragraphs(self, text: str, max_tokens: int) -> List[str]:
        """Split text by paragraphs"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if self.count_tokens(current_chunk + paragraph) <= max_tokens:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # If single paragraph is too long, split it
                if self.count_tokens(paragraph) > max_tokens:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    temp_chunk = ""
                    for sentence in sentences:
                        if self.count_tokens(temp_chunk + sentence) <= max_tokens:
                            if temp_chunk:
                                temp_chunk += " " + sentence
                            else:
                                temp_chunk = sentence
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sentence

                    if temp_chunk:
                        current_chunk = temp_chunk
                    else:
                        current_chunk = paragraph
                else:
                    current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def translate_chunk(self, chunk: str, target_language: str, source_language: str = "en") -> str:
        """Translate a single chunk using OpenAI API"""
        if not chunk.strip():
            return chunk

        # Construct the prompt with strict faithfulness requirements
        prompt = f"""You are a professional academic translator. Your task is to translate the following text from {source_language} to {target_language}.

CRITICAL REQUIREMENTS:
1. Translate EXACTLY what is provided - DO NOT add any content that is not in the original text
2. DO NOT add explanations, examples, or clarifications that are not in the source
3. DO NOT omit any information from the original text
4. Preserve all LaTeX commands, mathematical formulas, and technical notation exactly as they appear
5. Maintain the original structure, formatting, and paragraph breaks
6. Translate ONLY the text content, keeping all non-text elements unchanged
7. If you encounter ambiguous terms, choose the most literal translation rather than adding explanatory context

Text to translate:
{chunk}

Translated text (strictly faithful to original):"""

        try:
            # Make API request with enhanced prompt
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a precise academic translator specializing in mathematical and technical documents. Your primary directive is absolute faithfulness to the source text. NEVER add, remove, or modify information that is not explicitly part of the translation process. Preserve all formatting, mathematical notation, and technical terms exactly as written. Your role is translation ONLY, not explanation or elaboration."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature
                },
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                translated_text = data["choices"][0]["message"]["content"].strip()
                return translated_text
            else:
                raise ValueError("Invalid response format from OpenAI API")

        except requests.exceptions.RequestException as e:
            print(f"OpenAI API request failed: {e}")
            # Fallback to original text if API fails
            return chunk
        except (KeyError, ValueError) as e:
            print(f"Failed to parse OpenAI API response: {e}")
            return chunk
        except Exception as e:
            print(f"Unexpected error during translation: {e}")
            return chunk

    def translate(self, text: str, target_language: str, source_language: str = "en") -> str:
        """Translate text using OpenAI API with chunking support"""
        if not text.strip():
            return text

        # Check if text needs to be chunked
        if self.count_tokens(text) <= self.chunk_size:
            # Small text, translate directly
            return self.translate_chunk(text, target_language, source_language)

        # Large text, split into chunks and translate
        print(f"Text too large ({self.count_tokens(text)} tokens), splitting into chunks...")
        chunks = self.split_text_into_chunks(text, target_language, source_language)
        print(f"Split into {len(chunks)} chunks")

        translated_chunks = []
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            print(f"Translating chunk {i+1}/{total_chunks}...")

            # Add delay to avoid rate limiting
            if i > 0:
                time.sleep(1)

            translated_chunk = self.translate_chunk(chunk, target_language, source_language)
            translated_chunks.append(translated_chunk)

        # Combine translated chunks
        result = "\n\n".join(translated_chunks)
        print("All chunks translated successfully")

        return result

    def __call__(self, text: str, target_language: str, source_language: str = "en") -> str:
        """Make the translator callable"""
        return self.translate(text, target_language, source_language)