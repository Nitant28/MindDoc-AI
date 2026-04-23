# Multi-language support config (example)
LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'ur': 'Urdu',
}

def get_translation(key, lang='en'):
    # Placeholder: Integrate with translation API or local files
    translations = {
        'welcome': {
            'en': 'Welcome!',
            'hi': 'स्वागत है!',
            'bn': 'স্বাগতম!',
            'ta': 'வரவேற்கிறோம்!',
            'te': 'స్వాగతం!',
            'mr': 'स्वागत आहे!',
            'gu': 'સ્વાગત છે!',
            'kn': 'ಸ್ವಾಗತ!',
            'ml': 'സ്വാഗതം!',
            'pa': 'ਜੀ ਆਇਆਂ ਨੂੰ!',
            'ur': 'خوش آمدید!',
        }
    }
    return translations.get(key, {}).get(lang, translations.get(key, {}).get('en', key))

# Example usage:
# print(get_translation('welcome', 'hi'))
