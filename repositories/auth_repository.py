from db import supabase, service_supabase
from utils.logger import log_error, log_info

class AuthRepository:
    """
    Handles all direct interactions with Supabase Auth and User-related tables.
    """
    service_supabase = service_supabase
    @staticmethod
    def sign_in(email, password):
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

    @staticmethod
    def sign_up(email, password, options=None):
        return supabase.auth.sign_up({"email": email, "password": password, "options": options})

    @staticmethod
    def sign_out():
        return supabase.auth.sign_out()

    @staticmethod
    def get_session():
        return supabase.auth.get_session()

    @staticmethod
    def refresh_session(refresh_token):
        return supabase.auth.refresh_session(refresh_token)

    @staticmethod
    def set_session(access_token, refresh_token):
        return supabase.auth.set_session(access_token, refresh_token)

    @staticmethod
    def verify_otp(email, token, otp_type="signup"):
        return supabase.auth.verify_otp({"email": email, "token": token, "type": otp_type})

    @staticmethod
    def resend_otp(email, otp_type="signup"):
        return supabase.auth.resend({"type": otp_type, "email": email})

    @staticmethod
    def get_user_profile(user_id):
        """Fetch basic profile data."""
        try:
            res = service_supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            return res.data
        except Exception as e:
            log_error(f"AuthRepository Error (get_user_profile): {e}")
            return None

    @staticmethod
    def upsert_profile(profile_data):
        """Update or create user profile."""
        try:
            return service_supabase.table("profiles").upsert(
                profile_data, 
                on_conflict="id", 
                ignore_duplicates=True
            ).execute()
        except Exception as e:
            log_error(f"AuthRepository Error (upsert_profile): {e}")
            raise e
