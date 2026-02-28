"""
BizNode – Digital Business Operator
Copyright 2026 1BZ DZIT DAO LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---

BizNode LLM Service
===================
Wrapper for Ollama (Qwen2.5 4GB) for reasoning and decision intelligence.
This service handles all LLM interactions within the BizNode system.

Core Principle:
- Ollama (Qwen2.5 4GB) = Reasoning + decision intelligence
- LangGraph orchestrates when and how Ollama is used
"""

import requests
import json
import os
from typing import Dict, Any, Optional

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
MODEL = os.getenv("LLM_MODEL", "qwen2.5")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


def ask_llm(
    prompt: str,
    model: str = None,
    temperature: float = 0.7,
    stream: bool = False,
    system_prompt: Optional[str] = None
) -> str:
    """
    Send a prompt to Ollama and get the response.
    
    Args:
        prompt: The user prompt
        model: Model to use (default: qwen2.5)
        temperature: Sampling temperature
        stream: Whether to stream response
        system_prompt: Optional system prompt for context
    
    Returns:
        The LLM response text
    """
    model = model or MODEL
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "temperature": temperature
    }
    
    if system_prompt:
        payload["system"] = system_prompt
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: Ollama is not running. Please start Ollama."
    except requests.exceptions.Timeout:
        return "ERROR: LLM request timed out."
    except Exception as e:
        return f"ERROR: {str(e)}"


def generate_embedding(text: str) -> list:
    """
    Generate embedding vector for text using Ollama.
    
    Args:
        text: Text to embed
    
    Returns:
        Embedding vector as list of floats
    """
    try:
        response = requests.post(
            OLLAMA_EMBED_URL,
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("embedding", [])
    except requests.exceptions.ConnectionError:
        print("ERROR: Ollama is not running for embeddings")
        return []
    except Exception as e:
        print(f"ERROR generating embedding: {e}")
        return []


# === LLM-POWERED NODES ===

def parse_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intent Parsing Node - Uses LLM to extract business name and intent from user message.
    This is the first AI involvement in the registration flow.
    """
    prompt = f"""
    Extract business name from the request:
    
    "{state.get('raw_input', '')}"
    
    Return only business name.
    """
    
    business_name = ask_llm(prompt)
    state["business_name"] = business_name.strip()
    state["status"] = "intent_parsed"
    return state


def decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI Decision Node - Uses LLM for reasoning instead of simple if-else.
    Evaluates whether registration or action should proceed.
    """
    prompt = f"""
    Business name: {state.get('business_name', '')}
    Status: {state.get('status', '')}
    
    Should registration proceed?
    
    Answer yes or no.
    """
    
    decision = ask_llm(prompt)
    
    if "no" in decision.lower():
        state["status"] = "blocked"
    else:
        state["status"] = "approved"
    
    return state


def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intent Classifier for Multi-Bot Orchestration.
    Classifies request into: finance, marketing, legal, core
    """
    prompt = f"""
    Classify this request into one of these categories:
    finance, marketing, legal, core
    
    Request:
    {state.get('query', '')}
    
    Return only the category name.
    """
    
    state["route"] = ask_llm(prompt).strip().lower()
    return state


def extract_lead_info(message: str) -> Dict[str, Any]:
    """
    LLM Structured Extraction - Extracts structured data from marketing leads.
    Returns: name, business, contact
    """
    prompt = f"""
    Extract the following from this message:
    - name
    - business  
    - contact
    
    Message:
    {message}
    
    Return JSON format.
    """
    
    result = ask_llm(prompt)
    
    # Try to parse JSON from response
    try:
        # Find JSON in response
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return {"name": "", "business": "", "contact": ""}


def summarize_note(content: str) -> str:
    """
    LLM Summarizer - Auto-summarizes business notes in 3 lines.
    Used in Memory Write Pipeline.
    """
    prompt = f"""
    Summarize this business note in 3 lines:
    
    {content}
    """
    return ask_llm(prompt)


def generate_tags(content: str) -> str:
    """
    Auto Tag Generator - Extracts 5 relevant business tags.
    Used in Memory Write Pipeline.
    """
    prompt = f"""
    Extract 5 relevant business tags from:
    
    {content}
    
    Return comma separated.
    """
    return ask_llm(prompt)


def assess_risk(action_description: str) -> str:
    """
    LLM Risk Scoring - Categorizes risk as low, medium, or high.
    Used in Decision Authority Graph.
    """
    prompt = f"""
    Categorize risk level as low, medium, or high:
    
    {action_description}
    
    Return only one word: low, medium, or high.
    """
    return ask_llm(prompt).strip().lower()


def generate_response(context: str, query: str) -> str:
    """
    RAG Response Generator - Uses LLM with context from Qdrant.
    """
    prompt = f"""
    Using this business memory:
    
    {context}
    
    Answer:
    {query}
    """
    return ask_llm(prompt)


# === SYSTEM PROMPTS ===

SYSTEM_PROMPT = """You are BizNode AI, an autonomous business executive agent.
You help businesses manage leads, make decisions, and network with associates.
You operate with owner oversight but can act autonomously within defined risk levels.
Always be professional, concise, and helpful."""


def ask_biznode(prompt: str, context: Optional[Dict] = None) -> str:
    """
    Main entry point for BizNode LLM interactions.
    Includes system context for business operations.
    """
    full_prompt = prompt
    if context:
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        full_prompt = f"Context:\n{context_str}\n\nUser: {prompt}"
    
    return ask_llm(full_prompt, system_prompt=SYSTEM_PROMPT)
