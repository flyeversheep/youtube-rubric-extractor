"""
LLM client wrapper supporting OpenAI and z.ai
"""
import os
from typing import Optional, Dict, Any
from openai import OpenAI


class LLMClient:
    """Unified LLM client supporting multiple providers"""
    
    def __init__(self):
        self.provider = None
        self.client = None
        self.model = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate client based on env vars"""
        openai_key = os.getenv('OPENAI_API_KEY', '')
        zai_key = os.getenv('ZAI_API_KEY', '')
        provider_pref = os.getenv('AI_PROVIDER', 'auto')
        
        # Try z.ai first if preferred or auto with zai key available
        if provider_pref in ('zai', 'auto') and zai_key:
            try:
                self.client = OpenAI(
                    api_key=zai_key,
                    base_url=os.getenv('ZAI_BASE_URL', 'https://api.z.ai/api/paas/v4/')
                )
                self.provider = 'zai'
                self.model = os.getenv('AI_MODEL', 'glm-4.6')
                print(f"INFO: Using z.ai ({self.model})")
                return
            except Exception as e:
                print(f"WARN: Failed to init z.ai: {e}")
        
        # Fall back to OpenAI
        if openai_key:
            try:
                self.client = OpenAI(api_key=openai_key)
                self.provider = 'openai'
                self.model = os.getenv('AI_MODEL', 'gpt-4o-mini')
                print(f"INFO: Using OpenAI ({self.model})")
                return
            except Exception as e:
                print(f"WARN: Failed to init OpenAI: {e}")
        
        print("WARN: No LLM client configured. Set OPENAI_API_KEY or ZAI_API_KEY.")
    
    def is_available(self) -> bool:
        """Check if LLM client is ready"""
        return self.client is not None
    
    def complete(self, 
                 prompt: str, 
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.3,
                 max_tokens: int = 4000,
                 json_mode: bool = True) -> Dict[str, Any]:
        """
        Get completion from LLM
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Creativity (0-1)
            max_tokens: Max response length
            json_mode: Request JSON output
        
        Returns:
            Dict with 'success', 'content', 'error' keys
        """
        if not self.client:
            return {'success': False, 'error': 'LLM not configured', 'content': None}
        
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        try:
            params = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            
            # Add response format for JSON mode
            if json_mode and self.provider == 'openai':
                params['response_format'] = {'type': 'json_object'}
            
            # z.ai specific parameters
            if self.provider == 'zai':
                params['extra_body'] = {'thinking': {'type': 'disabled'}}
            
            response = self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            
            # Handle z.ai reasoning_content if present
            if not content and hasattr(response.choices[0].message, 'reasoning_content'):
                content = response.choices[0].message.reasoning_content
            
            return {
                'success': True,
                'content': content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'content': None}
    
    def complete_with_retry(self, 
                           prompt: str, 
                           system_prompt: Optional[str] = None,
                           retries: int = 2,
                           **kwargs) -> Dict[str, Any]:
        """Complete with automatic retries"""
        for attempt in range(retries + 1):
            result = self.complete(prompt, system_prompt, **kwargs)
            if result['success']:
                return result
            
            if attempt < retries:
                print(f"Retry {attempt + 1}/{retries}...")
        
        return result


# Global client instance
_client = None

def get_client() -> LLMClient:
    """Get or create global LLM client"""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_client():
    """Reset global client (useful for testing)"""
    global _client
    _client = None
