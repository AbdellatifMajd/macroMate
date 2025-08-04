from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai
import json
import re
import requests
from datetime import datetime
import logging


app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini setup
genai.configure(api_key="AIzaSyDu1V00qoUrJ0agU1TNnF4rvF03i0OtI24")
model = genai.GenerativeModel("gemini-2.5-flash")

# Unsplash setup
UNSPLASH_ACCESS_KEY = "f8Ji3_NX7ic_r4ijnnbpIUZac0Mvy-NcKyAGiIO4D70"

def get_unsplash_image(query):
    """Fetch a single image URL from Unsplash for a given query."""
    url = f"https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "client_id": UNSPLASH_ACCESS_KEY
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("results"):
            return data["results"][0]["urls"]["regular"]
    except Exception as e:
        logger.error(f"Unsplash error for '{query}': {e}")
    return None




@app.route('/api/foods', methods=['GET'])
def get_foods():
    """Fetch a list of foods based on a query"""
    query = request.args.get("query", "healthy food")
    prompt = f"""
    Provide a list of 3 {query} items in the following strict JSON format:
    [{{
        "name": "Food name",
        "category": "Category (e.g., fruit, vegetable, protein, grain)",
        "calories_per_100g": number
    }}, ...]
    
    Make sure the response is valid JSON only. Do NOT add any explanation or markdown.
    """
    
    try:
        response = model.generate_content(prompt)
    
        
        raw_text = response.text.strip()
        logger.info(f"Raw Gemini response:\n{raw_text}")
        
        # Remove markdown if present
        if raw_text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1).strip()
        
        food_data = json.loads(raw_text)
        
        # Attach Unsplash images
        for item in food_data:
            image_url = get_unsplash_image(item["name"])
            item["image"] = image_url if image_url else "https://via.placeholder.com/300?text=No+Image"
        
        return jsonify({"foods": food_data})
        
    except json.JSONDecodeError:
        return jsonify({
            "error": "Failed to parse Gemini response as JSON.",
            "raw_response": raw_text
        }), 500
    except Exception as e:
        logger.error(f"Error in get_foods: {e}")
        return jsonify({"error": str(e)}), 500
    





@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    """Main chat endpoint that processes user messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        user_profile = data.get('user_profile', {})
        conversation_history = data.get('conversation_history', [])
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Build conversation context
        context_messages = []
        for msg in conversation_history[-5:]:  # Keep last 5 messages for context
            role = "User" if not msg.get('isBot', False) else "FitBot"
            context_messages.append(f"{role}: {msg.get('text', '')}")
        
        conversation_context = "\n".join(context_messages) if context_messages else ""
        
        # Create a comprehensive prompt for nutrition advice
        nutrition_prompt = f"""You are FitBot, an expert AI nutritionist and fitness advisor. You provide personalized, evidence-based advice about nutrition, meal planning, and healthy eating.

User Profile:
- Name: {user_profile.get('fullName', 'User')}
- Email: {user_profile.get('email', 'Not provided')}
- Fitness Goal: {user_profile.get('fitness_goal', 'general health')}
- Body Type: {user_profile.get('body_type', 'not specified')}
- Preferred Macro Split: {user_profile.get('macro_split', 'not specified')}

Recent Conversation Context:
{conversation_context}

Guidelines for your responses:
1. Be helpful, friendly, and professional
2. Provide evidence-based nutrition advice
3. Consider the user's fitness goals and body type
4. Keep responses concise but informative (2-4 sentences ideal)
5. Use encouraging and motivational language
6. If asked about medical conditions, recommend consulting healthcare professionals
7. Focus on nutrition, meal planning, food choices, and healthy eating habits
8. Use emojis sparingly to keep responses friendly
9. Reference previous conversation when relevant

Current User Question: {user_message}

Provide a helpful response as FitBot:"""

        # Generate response using Gemini
        response = model.generate_content(nutrition_prompt)
        ai_response = response.text.strip()
        
        # Clean up the response
        ai_response = ai_response.replace('**', '').replace('*', '')
        
        return jsonify({
            'response': ai_response,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            'response': "I'm having some technical difficulties right now. Please try asking your question again! 🤖",
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        }), 500
    











if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
