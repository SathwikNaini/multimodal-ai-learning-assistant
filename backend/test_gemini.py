import sys
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Define function to test connection
def test_connection():
    # Find potential locations for .env files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, '..'))
    
    env_paths = [
        os.path.join(root_dir, '.env'),
        os.path.join(root_dir, '.env.local'),
        os.path.join(current_dir, '.env'),
    ]

    for path in env_paths:
        if os.path.exists(path):
            load_dotenv(path)

    # Fallback to general load_dotenv
    load_dotenv()

    # 1. Load GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("----------------------------------------")
    print("Gemini Connectivity Diagnostic Test")
    print("----------------------------------------")
    print(f"SDK version: {genai.__version__}")
    
    if not api_key:
        print("API Key validation: FAILED (GEMINI_API_KEY is missing/empty)")
        print("Success/Failure: FAILURE")
        return False
        
    key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "too_short"
    print(f"API Key exists: True (Preview: {key_preview}, Length: {len(api_key)})")
    
    # 2. Initialize Gemini
    genai.configure(api_key=api_key)
    
    model_name = "gemini-2.5-flash"
    print(f"Model used: {model_name}")
    
    try:
        # 3. Call gemini-2.5-flash with 4. "Respond with OK"
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Respond with OK")
        
        # 5. Print results
        print(f"Response text: {response.text.strip()}")
        print("Success/Failure: SUCCESS")
        return True
    except Exception as e:
        print(f"Response text: N/A")
        print(f"Success/Failure: FAILURE (Error details: {str(e)})")
        
        fallback_model_name = "gemini-2.5-flash"
        print(f"\nAttempting fallback test with model: {fallback_model_name}")
        try:
            model = genai.GenerativeModel(fallback_model_name)
            response = model.generate_content("Respond with OK")
            print(f"Response text: {response.text.strip()}")
            print("Success/Failure (Fallback): SUCCESS")
            return True
        except Exception as fallback_err:
            print(f"Response text (Fallback): N/A")
            print(f"Success/Failure (Fallback): FAILURE (Error details: {str(fallback_err)})")
            
        return False

if __name__ == "__main__":
    test_connection()
