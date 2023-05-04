import os

if "GOOGLE_API_KEY" in os.environ and os.environ["GOOGLE_API_KEY"] != "":
    print("API key present")
print("Hello world")