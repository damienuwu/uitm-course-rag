import subprocess
import json
import requests
from typing import Optional, Dict, Any, Generator
from .config import OLLAMA_MODEL, OLLAMA_API_URL

# Try to use requests if available, fallback to subprocess
USE_API = True

def query_ollama(
    prompt: str, 
    model: Optional[str] = None,  # Added model parameter
    max_tokens: int = 2048, 
    temperature: float = 0.3,
    timeout: int = 120
) -> str:
    """
    Query Ollama with optimized settings.
    
    Args:
        prompt: The input prompt
        model: Specific model to use (defaults to config OLLAMA_MODEL)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
        timeout: Request timeout in seconds
    
    Returns:
        Generated text response
    """
    # Use the provided model or fallback to the default in config
    target_model = model or OLLAMA_MODEL

    if USE_API:
        return _query_ollama_api(prompt, target_model, max_tokens, temperature, timeout)
    else:
        return _query_ollama_cli(prompt, target_model, timeout)


def _query_ollama_api(
    prompt: str, 
    model: str, 
    max_tokens: int, 
    temperature: float,
    timeout: int
) -> str:
    """
    Query Ollama via HTTP API (recommended - faster and more reliable)
    """
    try:
        payload = {
            "model": model,  # Use the passed model
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_k": 40,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096,  # Context window
                "stop": ["\n\n\n", "==="],  # Stop sequences
            }
        }
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json=payload,
            timeout=timeout
        )
        
        response.raise_for_status()
        data = response.json()
        
        if "response" in data:
            return data["response"].strip()
        else:
            print(f"⚠️ Unexpected response format: {data}")
            return "⚠️ Format respons tidak dijangka daripada Ollama."
            
    except requests.exceptions.Timeout:
        print(f"❌ Ollama API timeout after {timeout}s")
        return f"⚠️ Permintaan tamat masa selepas {timeout} saat. Model mungkin terlalu besar atau pelayan sibuk."
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama API. Is Ollama running?")
        return "⚠️ Tidak dapat menyambung ke Ollama. Sila pastikan Ollama sedang berjalan."
        
    except Exception as e:
        print(f"❌ Ollama API error: {e}")
        return f"⚠️ Ralat API Ollama: {str(e)}"


def _query_ollama_cli(prompt: str, model: str, timeout: int) -> str:
    """
    Query Ollama via CLI (fallback method)
    """
    try:
        result = subprocess.run(
            ["ollama", "run", model],  # Use the passed model
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout
        )

        output = result.stdout.decode("utf-8").strip()

        if not output:
            print("⚠️ Ollama returned no output.")
            stderr = result.stderr.decode("utf-8")
            if stderr:
                print(f"stderr: {stderr}")
            return "⚠️ Tiada respons daripada model Ollama."

        # Try to parse JSON response (in case CLI returns JSON)
        try:
            data = json.loads(output)
            if "response" in data:
                return data["response"].strip()
        except json.JSONDecodeError:
            pass  # Output is plain text

        return output

    except subprocess.TimeoutExpired:
        print(f"❌ Ollama CLI timeout after {timeout}s")
        return f"⚠️ Permintaan tamat masa selepas {timeout} saat."
        
    except FileNotFoundError:
        print("❌ Ollama CLI not found. Is Ollama installed?")
        return "⚠️ Ollama tidak dijumpai. Sila pastikan Ollama telah dipasang."
        
    except Exception as e:
        print(f"❌ Error querying Ollama CLI: {e}")
        return f"⚠️ Ralat semasa berinteraksi dengan Ollama: {str(e)}"


def query_ollama_stream(
    prompt: str,
    model: Optional[str] = None,  # Added model parameter
    max_tokens: int = 2048,
    temperature: float = 0.3,
    timeout: int = 120
) -> Generator[str, None, None]:
    """
    Query Ollama with streaming response (for real-time UI updates)
    """
    target_model = model or OLLAMA_MODEL

    try:
        payload = {
            "model": target_model,  # Use the passed model
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_k": 40,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096,
            }
        }
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=timeout
        )
        
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        yield f"⚠️ Ralat: {str(e)}"


def check_ollama_health() -> Dict[str, Any]:
    """
    Check if Ollama is running and accessible
    
    Returns:
        Dictionary with status information
    """
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        response.raise_for_status()
        
        models = response.json().get("models", [])
        model_names = [m.get("name") for m in models]
        
        return {
            "status": "healthy",
            "available_models": model_names,
            "selected_model": OLLAMA_MODEL,
            "model_loaded": OLLAMA_MODEL in model_names
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Cannot connect to Ollama. Is it running?",
            "hint": "Run: ollama serve"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def load_model(model_name: str) -> Dict[str, Any]:
    """
    Preload a model into memory
    
    Args:
        model_name: Name of the model to load
    
    Returns:
        Status dictionary
    """
    try:
        # Send a small request to load the model
        payload = {
            "model": model_name,
            "prompt": "Hello",
            "stream": False,
            "options": {"num_predict": 1}
        }
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Model {model_name} loaded successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load model: {str(e)}"
        }