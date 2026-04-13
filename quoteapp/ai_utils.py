# import openai
# from django.conf import settings

# openai.api_key = settings.OPENAI_API_KEY

# def enhance_service_description(original_description, service_category=None, urgency_type='normal'):
#     """
#     Enhance service description using OpenAI API
    
#     Args:
#         original_description: Raw description from user
#         service_category: Category name for context
#         urgency_type: 'normal' or 'urgent'
    
#     Returns:
#         Enhanced description or original if API fails
#     """
#     if not original_description or len(original_description.strip()) < 10:
#         return original_description
    
#     try:
#         prompt = f"""You are a professional service marketplace assistant. 
# Enhance this service description to be clear, professional, and customer-friendly.
# Keep it concise (max 150 words). Maintain the original intent.

# Category: {service_category or 'General Service'}
# Urgency: {urgency_type}
# Original Description: {original_description}

# Enhanced Description:"""

#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a professional service description writer."},
#                 {"role": "user", "content": prompt}
#             ],
#             max_tokens=200,
#             temperature=0.7
#         )
        
#         enhanced = response.choices[0].message.content.strip()
#         return enhanced if enhanced else original_description
        
#     except Exception as e:
#         print(f"AI enhancement failed: {str(e)}")
#         return original_description  # Fallback to original
    


from openai import OpenAI
from django.conf import settings

def _get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


# def enhance_service_description(original_description, service_category=None, urgency_type='normal'):
#     """
#     Enhance service description using OpenAI API
#     """
#     if not original_description or len(original_description.strip()) < 10:
#         return original_description
    
#     try:
#         prompt = f"""You are a professional service marketplace assistant. 
# Enhance this service description to be clear, professional, and customer-friendly.
# Keep it concise (max 150 words). Maintain the original intent.

# Category: {service_category or 'General Service'}
# Urgency: {urgency_type}
# Original Description: {original_description}

# Enhanced Description:"""

#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a professional service description writer."},
#                 {"role": "user", "content": prompt}
#             ],
#             max_tokens=200,
#             temperature=0.7
#         )
        
#         enhanced = response.choices[0].message.content.strip()
#         return enhanced if enhanced else original_description
        
#     except Exception as e:
#         print(f"AI enhancement failed: {str(e)}")
#         return original_description
    
def enhance_service_description(original_description, service_category=None, urgency_type='normal', message_type='offer'):
    """
    message_type: 'offer' or 'order'
    """
    if not original_description or len(original_description.strip()) < 10:
        return original_description
    client = _get_openai_client()
    if client is None:
        return original_description
    
    try:
        # ✅ DIFFERENT PROMPTS FOR OFFER VS ORDER
        if message_type == 'offer':
            prompt = f"""You are a professional service marketplace assistant. 
Enhance this service OFFER description to be clear, professional, and customer-friendly.
Keep it concise (max 150 words). Maintain the original intent.

Category: {service_category or 'General Service'}
Urgency: {urgency_type}
Original Description: {original_description}

Enhanced Offer Description:"""
        
        else:  # message_type == 'order'
            prompt = f"""You are a professional service marketplace assistant.
        Create a friendly ORDER CONFIRMATION message thanking the customer.
        Express gratitude, mention we're happy to assist with future issues, and encourage ratings.
        Keep it warm and professional (max 100 words).
        DO NOT include any signature, closing phrases like "Warm regards", "Sincerely", or company name placeholders.

        Service Category: {service_category or 'General Service'}
        Original Work: {original_description}

        Order Confirmation Message:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional service description writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        enhanced = response.choices[0].message.content.strip()
        return enhanced if enhanced else original_description
        
    except Exception as e:
        print(f"AI enhancement failed: {str(e)}")
        return original_description