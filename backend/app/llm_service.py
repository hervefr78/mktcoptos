"""
LLM Service that dynamically uses settings to select provider and model
"""
import httpx
import os
import logging
import traceback
import asyncio
from typing import Optional, AsyncGenerator, Callable, Any
from sqlalchemy.orm import Session

# Import from settings_service (database-backed)
from .settings_service import SettingsService
from .database import SessionLocal

# Set up logging
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with LLM providers based on settings"""

    @staticmethod
    async def _retry_with_backoff(
        func: Callable,
        max_retries: int = 4,
        initial_delay: float = 2.0,
        operation_name: str = "operation"
    ) -> Any:
        """
        Retry a function with exponential backoff on network errors.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts (default 4)
            initial_delay: Initial delay in seconds (default 2.0)
            operation_name: Name of operation for logging

        Returns:
            Result from the function call

        Raises:
            Last exception if all retries fail
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await func()
            except (
                httpx.NetworkError,
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
                httpx.RemoteProtocolError
            ) as e:
                last_exception = e

                if attempt < max_retries:
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff: 2s, 4s, 8s, 16s
                else:
                    logger.error(
                        f"{operation_name} failed after {max_retries + 1} attempts: {type(e).__name__}: {str(e)}"
                    )
            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx) except 429 (rate limit) and 408 (timeout)
                if e.response.status_code in [429, 408, 503, 504]:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{operation_name} got retryable HTTP status {e.response.status_code} "
                            f"(attempt {attempt + 1}/{max_retries + 1}). Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(
                            f"{operation_name} failed after {max_retries + 1} attempts with HTTP {e.response.status_code}"
                        )
                else:
                    # Don't retry other client errors
                    raise

        # If we get here, all retries failed
        if last_exception:
            raise last_exception

    @staticmethod
    async def generate(
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        user_id: int = 1  # Default to user 1 (admin) for now
    ):
        """
        Generate text using the configured LLM provider

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            user_id: User ID to load settings for

        Returns:
            Generated text or async generator if streaming
        """
        # Load settings from database
        db = SessionLocal()
        try:
            settings = SettingsService.get_combined_settings(user_id, db)
        finally:
            db.close()

        if settings.llmProvider == 'openai':
            return await LLMService._generate_openai(
                prompt, system_prompt, temperature, max_tokens, stream, settings
            )
        else:  # ollama
            return await LLMService._generate_ollama(
                prompt, system_prompt, temperature, max_tokens, stream, settings
            )

    @staticmethod
    async def _generate_openai(
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool,
        settings
    ):
        """Generate using OpenAI API

        Tries Responses API first (for GPT-5 models), falls back to Chat Completions API
        """
        api_key = settings.openaiApiKey or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        model = settings.llmModel or "gpt-4o-mini"

        # Log model selection for debugging
        logger.info(f"Using OpenAI model: {model}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if settings.openaiOrganizationId:
            headers["OpenAI-Organization"] = settings.openaiOrganizationId

        # Determine timeout based on expected generation time
        # GPT-5 is slower than GPT-4, especially for long-form content
        # Use longer timeouts for content generation (>1500 tokens)
        if max_tokens > 8000:
            timeout = 480.0  # 8 minutes for very long content
        elif max_tokens > 1500:
            timeout = 360.0  # 6 minutes for article-length content
        else:
            timeout = 180.0  # 3 minutes for shorter content (increased from 2 min for GPT-5)

        # Check model capabilities (based on othefapp working implementation)
        model_lower = model.lower()

        # Determine if model supports custom temperature
        # GPT-5.1 models DO support temperature
        # GPT-5 base, O1, O4 do NOT support custom temperature
        supports_temperature = True
        if model_lower.startswith('gpt-5.1'):
            supports_temperature = True
        elif any([model_lower.startswith(prefix) for prefix in ['gpt-5', 'o1', 'o3', 'o4']]):
            supports_temperature = False

        # Check if model supports verbosity parameter (GPT-5 models)
        supports_verbosity = model_lower.startswith('gpt-5')

        # Check if model supports reasoning effort (o1, o3, o4 models)
        supports_reasoning = any([model_lower.startswith(prefix) for prefix in ['o1', 'o3', 'o4']])

        # Log model capabilities
        logger.info(f"Model {model} capabilities: temp={supports_temperature}, verbosity={supports_verbosity}, reasoning={supports_reasoning}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            if stream:
                # For streaming, use Chat Completions API (Responses API streaming not yet implemented)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                # Determine token parameter based on model
                uses_new_param = any([
                    model.startswith('gpt-5'),
                    model.startswith('gpt-4.1'),
                    model.startswith('o1'),
                    model.startswith('o3'),
                    model.startswith('o4')
                ])
                token_param = 'max_completion_tokens' if uses_new_param else 'max_tokens'

                payload = {
                    "model": model,
                    "messages": messages,
                    token_param: max_tokens,
                    "stream": True
                }

                # Only add temperature if model supports it
                if supports_temperature:
                    payload["temperature"] = temperature

                # Add verbosity for GPT-5 models
                if supports_verbosity:
                    payload["verbosity"] = "medium"  # Options: low, medium, high

                # Add reasoning effort for o1/o3/o4 models
                if supports_reasoning:
                    payload["reasoning"] = {"effort": "medium"}  # Options: minimal, low, medium, high

                return LLMService._stream_openai(client, headers, payload)
            else:
                # Try Responses API first (supports GPT-5 and newer models)
                try:
                    logger.info(f"Trying Responses API for model={model}")
                    responses_payload = {
                        "model": model,
                        "input": prompt,
                        "max_output_tokens": max_tokens
                    }

                    # Add instructions (system prompt) if provided
                    if system_prompt:
                        responses_payload["instructions"] = system_prompt

                    # Only add temperature if model supports it
                    if supports_temperature:
                        responses_payload["temperature"] = temperature

                    # Add verbosity for GPT-5 models
                    if supports_verbosity:
                        responses_payload["verbosity"] = "medium"

                    # Add reasoning effort for o1/o3/o4 models
                    if supports_reasoning:
                        responses_payload["reasoning"] = {"effort": "medium"}

                    # Wrap API call with retry logic
                    async def _call_responses_api():
                        return await client.post(
                            "https://api.openai.com/v1/responses",
                            headers=headers,
                            json=responses_payload
                        )

                    response = await LLMService._retry_with_backoff(
                        _call_responses_api,
                        operation_name=f"OpenAI Responses API ({model})"
                    )

                    if response.status_code == 200:
                        data = response.json()
                        # Responses API returns content in 'output' field
                        if 'output' in data:
                            logger.info(f"✓ Responses API succeeded for {model}")
                            return data['output'] if isinstance(data['output'], str) else str(data['output'])
                        else:
                            logger.warning(f"Responses API returned 200 but no 'output' field: {list(data.keys())}")
                            # Fall through to Chat Completions API

                    elif response.status_code in [404, 400]:
                        # Responses API not available or model not supported, try Chat Completions
                        logger.info(f"Responses API not available (status {response.status_code}), falling back to Chat Completions API")
                    else:
                        # Other error from Responses API
                        error_text = response.text
                        logger.warning(f"Responses API error {response.status_code}, trying Chat Completions: {error_text[:200]}")

                except httpx.TimeoutException as e:
                    logger.error(f"Responses API timeout after {timeout}s with model {model}, max_tokens={max_tokens}")
                    logger.error(f"Consider using a smaller max_tokens value or expect longer wait times for GPT-5")
                    raise ValueError(f"Request timeout after {timeout} seconds. Try reducing content length or using a faster model.")
                except httpx.HTTPError as e:
                    logger.warning(f"Responses API request failed: {e}, trying Chat Completions API")

                # Fallback to Chat Completions API
                try:
                    logger.info(f"Using Chat Completions API for model={model}")
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})

                    # Determine which token parameter to use based on model
                    # GPT-5, GPT-4.1, o1, o3, o4 models require 'max_completion_tokens'
                    # GPT-4o and older models use 'max_tokens'
                    uses_new_param = any([
                        model.startswith('gpt-5'),
                        model.startswith('gpt-4.1'),
                        model.startswith('o1'),
                        model.startswith('o3'),
                        model.startswith('o4')
                    ])

                    token_param = 'max_completion_tokens' if uses_new_param else 'max_tokens'
                    logger.info(f"Using token parameter '{token_param}' for model {model}")

                    chat_payload = {
                        "model": model,
                        "messages": messages,
                        token_param: max_tokens
                    }

                    # Only add temperature if model supports it
                    if supports_temperature:
                        chat_payload["temperature"] = temperature

                    # Add verbosity for GPT-5 models (may be supported in Chat Completions)
                    if supports_verbosity:
                        chat_payload["verbosity"] = "medium"

                    # Add reasoning effort for o1/o3/o4 models
                    if supports_reasoning:
                        chat_payload["reasoning"] = {"effort": "medium"}

                    # Wrap API call with retry logic
                    async def _call_chat_completions_api():
                        return await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers=headers,
                            json=chat_payload
                        )

                    response = await LLMService._retry_with_backoff(
                        _call_chat_completions_api,
                        operation_name=f"OpenAI Chat Completions API ({model})"
                    )

                    if response.status_code != 200:
                        error_text = response.text
                        logger.error(f"OpenAI Chat Completions API error: status={response.status_code}, response={error_text}")
                        logger.error(f"Request payload: model={model}, messages_count={len(messages)}, max_tokens={max_tokens}, temperature={temperature}")

                        # Try to parse error details
                        try:
                            error_json = response.json()
                            error_msg = error_json.get('error', {}).get('message', error_text)
                            raise ValueError(f"OpenAI API error ({response.status_code}): {error_msg}")
                        except:
                            raise ValueError(f"OpenAI API error ({response.status_code}): {error_text}")

                    data = response.json()
                    logger.info(f"✓ Chat Completions API succeeded for {model}")
                    return data['choices'][0]['message']['content']
                except httpx.TimeoutException as e:
                    logger.error(f"Chat Completions API timeout after {timeout}s with model {model}, max_tokens={max_tokens}")
                    logger.error(f"This is normal for GPT-5 generating long content. Consider using gpt-4o or gpt-4o-mini for faster results.")
                    raise ValueError(f"Request timeout after {timeout} seconds generating content with {model}. GPT-5 can be slow for long content - try gpt-4o-mini for faster generation.")
                except httpx.HTTPError as e:
                    logger.error(f"HTTP error calling OpenAI Chat Completions: {e}")
                    raise ValueError(f"Failed to connect to OpenAI: {str(e)}")

    @staticmethod
    async def _stream_openai(client, headers, payload):
        """Stream OpenAI response"""
        try:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_text = error_text.decode('utf-8')
                    logger.error(f"OpenAI streaming API error: status={response.status_code}, response={error_text}")

                    # Try to parse error details
                    try:
                        import json
                        error_json = json.loads(error_text)
                        error_msg = error_json.get('error', {}).get('message', error_text)
                        raise ValueError(f"OpenAI API error ({response.status_code}): {error_msg}")
                    except json.JSONDecodeError:
                        raise ValueError(f"OpenAI API error ({response.status_code}): {error_text}")

                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            if chunk['choices'][0]['delta'].get('content'):
                                yield chunk['choices'][0]['delta']['content']
                        except:
                            continue
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during OpenAI streaming: {e}")
            raise ValueError(f"Failed to stream from OpenAI: {str(e)}")

    @staticmethod
    async def _generate_ollama(
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool,
        settings
    ):
        """Generate using Ollama API"""
        # Priority: environment variable > database settings > default
        base_url = os.getenv('OLLAMA_HOST') or settings.ollamaBaseUrl or 'http://localhost:11434'
        # Handle migration from old Docker URL
        if base_url in ["http://ollama:11434", "http://ollama:11434/"]:
            base_url = os.getenv('OLLAMA_HOST', "http://host.docker.internal:11434")
        model = settings.llmModel or "qwen2.5:7b"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                return LLMService._stream_ollama(client, base_url, payload)
            else:
                response = await client.post(
                    f"{base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data.get('response', '')

    @staticmethod
    async def _stream_ollama(client, base_url, payload):
        """Stream Ollama response"""
        async with client.stream(
            "POST",
            f"{base_url}/api/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        import json
                        chunk = json.loads(line)
                        if chunk.get('response'):
                            yield chunk['response']
                    except:
                        continue

    @staticmethod
    async def generate_image(
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        user_id: int = 1  # Default to user 1 (admin) for now
    ) -> str:
        """
        Generate image using configured provider

        Args:
            prompt: Image description prompt
            size: Image size (e.g., "1024x1024")
            quality: Image quality ("standard" or "hd")
            style: Image style ("natural" or "vivid")
            user_id: User ID to load settings for

        Returns:
            URL of generated image
        """
        # Load settings from database
        db = SessionLocal()
        try:
            settings = SettingsService.get_combined_settings(user_id, db)
            logger.info(f"Loaded settings for image generation: provider={settings.imageProvider}, model={getattr(settings, 'openaiImageModel', 'N/A')}")
        finally:
            db.close()

        # Use appropriate provider based on settings
        if settings.imageProvider == 'openai':
            logger.info(f"Using OpenAI for image generation")
            return await LLMService._generate_image_openai(prompt, size, quality, style, settings)
        elif settings.imageProvider == 'stable-diffusion':
            logger.info(f"Using Stable Diffusion for image generation")
            return await LLMService._generate_image_sd(prompt, settings)
        elif settings.imageProvider == 'comfyui':
            logger.info(f"Using ComfyUI for image generation")
            return await LLMService._generate_image_comfyui(prompt, size, settings)
        elif settings.imageProvider == 'hybrid':
            # Default to OpenAI for hybrid (can add logic to choose based on context)
            logger.info(f"Using hybrid (defaulting to OpenAI) for image generation")
            return await LLMService._generate_image_openai(prompt, size, quality, style, settings)
        else:
            logger.error(f"Unknown image provider: {settings.imageProvider}")
            raise ValueError(f"Unknown image provider: {settings.imageProvider}")

    @staticmethod
    async def _generate_image_openai(
        prompt: str,
        size: Optional[str],
        quality: Optional[str],
        style: Optional[str],
        settings
    ) -> str:
        """Generate image using OpenAI DALL-E or gpt-image-1"""
        api_key = settings.openaiApiKey or os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OpenAI API key not configured")

        model = settings.openaiImageModel or "gpt-image-1"

        # Handle different size formats for different models
        if model == "dall-e-3":
            # DALL-E 3 sizes: 1024x1024, 1792x1024, 1024x1792
            if size == "1536x1024":
                size = "1792x1024"
            elif size == "1024x1536":
                size = "1024x1792"
            size = size or settings.openaiImageSize or "1024x1024"
            quality = quality or settings.openaiImageQuality or "standard"
            style = style or settings.openaiImageStyle or "natural"
        else:
            # gpt-image-1 sizes: 1024x1024, 1024x1536, 1536x1024, auto
            if size == "1792x1024":
                size = "1536x1024"
            elif size == "1024x1792":
                size = "1024x1536"
            size = size or settings.openaiImageSize or "1024x1024"
            # gpt-image-1 quality: low, medium, high, auto (NOT hd/standard)
            if quality == "hd":
                quality = "high"
            elif quality == "standard":
                quality = "medium"
            quality = quality or "high"
            style = None  # gpt-image-1 doesn't support style

        logger.info(f"OpenAI image generation: model={model}, size={size}, quality={quality}, style={style}")

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size
        }

        # Add quality and style based on model
        if model == "dall-e-3":
            payload["quality"] = quality
            payload["style"] = style
            payload["response_format"] = "url"
        else:
            # gpt-image-1 - only supports quality parameter
            payload["quality"] = quality

        logger.info(f"Sending request to OpenAI images/generations API with payload keys: {list(payload.keys())}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Wrap API call with retry logic
                async def _call_image_api():
                    return await client.post(
                        "https://api.openai.com/v1/images/generations",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            **({"OpenAI-Organization": settings.openaiOrganizationId} if settings.openaiOrganizationId else {})
                        },
                        json=payload
                    )

                response = await LLMService._retry_with_backoff(
                    _call_image_api,
                    operation_name=f"OpenAI Image Generation ({model})"
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"OpenAI API error: status={response.status_code}, response={error_text}")
                    raise ValueError(f"OpenAI API error: {error_text}")

                data = response.json()
                logger.info(f"OpenAI API response structure: {list(data.keys())}")

                # Check if response has expected structure
                if 'data' not in data:
                    logger.error(f"Unexpected response structure. Full response: {data}")
                    raise ValueError(f"OpenAI API returned unexpected response structure: {data}")

                if not data['data'] or len(data['data']) == 0:
                    logger.error(f"No images in response. Full response: {data}")
                    raise ValueError(f"OpenAI API returned no images")

                # Check for url or b64_json
                image_data = data['data'][0]
                if 'url' in image_data:
                    url = image_data['url']
                    logger.info(f"Image generated successfully (URL): {url[:100]}...")
                    return url
                elif 'b64_json' in image_data:
                    b64_data = image_data['b64_json']
                    logger.info(f"Image generated successfully (base64)")
                    return f"data:image/png;base64,{b64_data}"
                else:
                    logger.error(f"Image data missing url and b64_json. Keys: {list(image_data.keys())}")
                    raise ValueError(f"OpenAI API response missing image URL or base64 data")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during image generation: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"OpenAI API error: {e.response.text}")
        except KeyError as e:
            logger.error(f"KeyError during image generation - missing key: {str(e)}")
            logger.error(f"Response data was: {data if 'data' in locals() else 'N/A'}")
            raise ValueError(f"OpenAI API response missing expected key: {str(e)}")
        except Exception as e:
            logger.error(f"Error during OpenAI image generation: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    async def _generate_image_sd(prompt: str, settings) -> str:
        """Generate image using Stable Diffusion"""
        base_url = settings.sdBaseUrl or "http://localhost:7860"

        payload = {
            "prompt": prompt,
            "steps": 20,
            "cfg_scale": 7.0,
            "width": 1024,
            "height": 1024
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{base_url}/sdapi/v1/txt2img",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            # Return base64 image data (would need to save to file/cloud in production)
            if data.get('images') and len(data['images']) > 0:
                return f"data:image/png;base64,{data['images'][0]}"
            else:
                raise ValueError("No image generated")

    @staticmethod
    async def _generate_image_comfyui(
        prompt: str,
        size: Optional[str],
        settings
    ) -> str:
        """Generate image using ComfyUI"""
        import asyncio
        import random

        # Priority: environment variable > database settings > default
        base_url = os.getenv('COMFYUI_BASE_URL') or getattr(settings, 'comfyuiBaseUrl', None) or 'http://localhost:8188'
        # Handle migration from old Docker URL
        if base_url in ["http://comfyui:8188", "http://comfyui:8188/"]:
            base_url = os.getenv('COMFYUI_BASE_URL', "http://host.docker.internal:8188")

        # Parse size
        width = 1024
        height = 1024
        if size:
            try:
                w, h = size.split('x')
                width = int(w)
                height = int(h)
            except:
                pass

        seed = random.randint(0, 1000000)
        model = getattr(settings, 'sdxlModel', None) or 'sd_xl_turbo_1.0_fp16.safetensors'
        steps = getattr(settings, 'sdxlSteps', None) or 6
        cfg_scale = getattr(settings, 'sdxlCfgScale', None) or 1.0
        sampler = getattr(settings, 'sdxlSampler', None) or 'euler_ancestral'
        negative_prompt = getattr(settings, 'imageNegativePrompt', None) or 'low quality, blurry, watermark'

        # Build ComfyUI workflow
        workflow = {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": sampler,
                    "scheduler": "karras",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": model
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "api_output",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }

        logger.info(f"ComfyUI image generation: model={model}, size={width}x{height}, steps={steps}")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Queue the workflow
                logger.info(f"Sending workflow to ComfyUI at {base_url}...")
                response = await client.post(
                    f"{base_url}/prompt",
                    json={"prompt": workflow},
                    timeout=10.0
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"ComfyUI queue error: {error_text}")
                    raise ValueError(f"ComfyUI error: {error_text}")

                prompt_id = response.json().get('prompt_id')
                logger.info(f"ComfyUI job queued: {prompt_id}")

                # Poll for completion
                max_attempts = 60
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)

                    history_response = await client.get(
                        f"{base_url}/history/{prompt_id}",
                        timeout=5.0
                    )

                    if history_response.status_code != 200:
                        continue

                    history = history_response.json().get(prompt_id, {})

                    if history and history.get('status', {}).get('completed'):
                        # Get the output image
                        outputs = history.get('outputs', {})
                        save_image_output = outputs.get("9", {})

                        if save_image_output and save_image_output.get('images'):
                            image_info = save_image_output['images'][0]
                            filename = image_info.get('filename')
                            subfolder = image_info.get('subfolder', '')
                            image_type = image_info.get('type', 'output')

                            # Fetch the image
                            image_url = f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={image_type}"
                            image_response = await client.get(image_url, timeout=30.0)

                            if image_response.status_code == 200:
                                import base64
                                base64_data = base64.b64encode(image_response.content).decode('utf-8')
                                logger.info(f"Image generated successfully with ComfyUI")
                                return f"data:image/png;base64,{base64_data}"

                    if attempt % 5 == 0:
                        logger.info(f"Still waiting for ComfyUI... ({attempt * 2}s)")

                raise ValueError(f"ComfyUI generation timeout after {max_attempts * 2} seconds")

        except httpx.ConnectError:
            logger.error(f"Cannot connect to ComfyUI at {base_url}")
            raise ValueError(f"Cannot connect to ComfyUI. Make sure ComfyUI is running at {base_url}")
        except Exception as e:
            logger.error(f"ComfyUI error: {str(e)}")
            raise
